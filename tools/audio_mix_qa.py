"""Read-only, measured FFmpeg audio QA (stdlib only; no speech/provider engines).

CLI: python tools/audio_mix_qa.py mix.wav --expect expectations.json
Prints JSON; exits 0 on success, 1 on failed checks, 2 on invalid input,
3 on unavailable FFmpeg/ffprobe, 4 on timeout. No files are written.

Optional expectation object (seconds, zero-based channel indices):
  {"channels": 2, "onsets": [0.3, 0.3], "onset_tolerance": 0.01,
   "duration": 2, "duration_tolerance": 0.01,
   "loudness": {"target_lufs": -16, "tolerance_lu": 1,
                "max_true_peak_dbtp": -1},
   "cues": [{"id": "short", "start": 0.3, "duration": 0.08,
             "fade_in": 0.04, "fade_out": 0.04, "channels": [0, 1],
             "max_tail_ratio": 0.3, "post_silence": 0.02}]}

Onsets are the first samples above --silence-db, per channel (null means
expected silence). Cue checks require isolated stems or nonoverlapping cue
windows: a final mix cannot identify which source produced a sample. Each cue
must fit the decoded timeline; declared fades must be disjoint and in bounds.
With fade_out > 0, the final min(10% of cue, 20% of fade) RMS is compared with
the loudest of ten cue windows; optional max_tail_ratio defaults to 0.3.
Optional post_silence seconds checks for leakage immediately after a cue;
that window must also be isolated and fully inside the decoded timeline.
This is envelope evidence, not a perceptual click or intelligibility verdict.
No mandatory delivery loudness target is imposed. Loudness always measures
FFmpeg loudnorm *input* statistics; null LUFS means silence/too-short material.

OpenMontage's audio_mixer.py informed the regression cases: delay all channels,
fade before delaying, disjoint short-cue fades, and verify actual LUFS rather
than assuming a requested normalization target was achieved. This module is
an independent probe; it does not import the upstream implementation.
"""

from __future__ import annotations

import argparse
from array import array
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys


ANALYSIS_RATE = 48000
MAX_PCM_BYTES = 256 * 1024 * 1024


def _number(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if not math.isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


def bounded_fades(duration, fade_in=0.0, fade_out=0.0):
    """Return a source-relative, nonoverlapping fade plan, never mutate a mix.

    Each fade is capped at half the cue, matching the short-segment safety
    rule. Feed these returned values to FFmpeg *before* the timeline delay.
    """
    duration = _number(duration, "duration", 0)
    if duration == 0:
        raise ValueError("duration must be positive")
    fi = min(_number(fade_in, "fade_in", 0), duration / 2)
    fo = min(_number(fade_out, "fade_out", 0), duration / 2)
    return {"fade_in": fi, "fade_out": fo, "fade_out_start": duration - fo}


def _run(command, timeout):
    completed = subprocess.run(command, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=timeout,
                               stdin=subprocess.DEVNULL, check=False)
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace")[-3000:]
        raise ValueError(f"{Path(command[0]).name} exited {completed.returncode}: {detail}")
    return completed


def _db(amplitude):
    return 20 * math.log10(amplitude) if amplitude > 0 else None


def _rms(samples):
    return math.sqrt(sum(x * x for x in samples) / len(samples)) if samples else 0.0


def _finite_stat(value):
    number = float(value)
    return number if math.isfinite(number) else None


def _validate_expect(expect):
    if not isinstance(expect, dict):
        raise ValueError("expectations must be a JSON object")
    allowed = {"channels", "onsets", "onset_tolerance", "duration",
               "duration_tolerance", "loudness", "cues"}
    unknown = expect.keys() - allowed
    if unknown:
        raise ValueError(f"unknown expectation fields: {sorted(unknown)}")
    if "channels" in expect:
        n = expect["channels"]
        if type(n) is not int or n < 1:
            raise ValueError("channels must be a positive integer")
    for key in ("onset_tolerance", "duration", "duration_tolerance"):
        if key in expect:
            _number(expect[key], key, 0)
    if "onsets" in expect:
        if not isinstance(expect["onsets"], list) or not expect["onsets"]:
            raise ValueError("onsets must be a nonempty list of seconds or null")
        for onset in expect["onsets"]:
            if onset is not None:
                _number(onset, "onset", 0)
    loudness = expect.get("loudness", {})
    if not isinstance(loudness, dict) or loudness.keys() - {
        "target_lufs", "tolerance_lu", "max_true_peak_dbtp"
    }:
        raise ValueError("invalid loudness expectation fields")
    for key, value in loudness.items():
        _number(value, key, 0 if key == "tolerance_lu" else None)
    cues = expect.get("cues", [])
    if not isinstance(cues, list):
        raise ValueError("cues must be a list")
    for cue in cues:
        if not isinstance(cue, dict) or cue.keys() - {
            "id", "start", "duration", "fade_in", "fade_out", "channels", "max_tail_ratio", "post_silence"
        }:
            raise ValueError("invalid cue fields")
        for key in ("start", "duration"):
            if key not in cue:
                raise ValueError(f"cue requires {key}")
            _number(cue[key], f"cue.{key}", 0)
        if cue["duration"] == 0:
            raise ValueError("cue duration must be positive")
        for key in ("fade_in", "fade_out", "max_tail_ratio", "post_silence"):
            if key in cue:
                _number(cue[key], f"cue.{key}", 0)
        if "channels" in cue:
            indices = cue["channels"]
            if (not isinstance(indices, list) or not indices
                    or any(type(i) is not int or i < 0 for i in indices)
                    or len(set(indices)) != len(indices)):
                raise ValueError("cue.channels must contain distinct nonnegative integers")


def probe_audio(path, expect=None, *, ffmpeg="ffmpeg", ffprobe="ffprobe",
                silence_db=-60.0, timeout=120.0, max_seconds=600.0):
    """Return JSON-safe measurements/checks; operational errors are structured.

    Decode first audio stream at 48 kHz float PCM, preserving channel count.
    Memory and duration limits reject oversized inputs, never report a prefix
    as a complete pass. timeout applies separately to each FFmpeg/ffprobe call.
    """
    result = {"schema_version": 1, "tool": "audio_mix_qa", "status": "failed",
              "input": str(path), "checks": [], "measurements": {}, "error": None}
    try:
        expect = {} if expect is None else expect
        _validate_expect(expect)
        silence_db = _number(silence_db, "silence_db")
        timeout = _number(timeout, "timeout", 0)
        max_seconds = _number(max_seconds, "max_seconds", 0)
        if timeout == 0 or max_seconds == 0 or silence_db >= 0:
            raise ValueError("timeout/max_seconds must be positive; silence_db must be < 0")
        resolved = {name: shutil.which(str(binary)) for name, binary in
                    (("ffmpeg", ffmpeg), ("ffprobe", ffprobe))}
        missing = [name for name, binary in resolved.items() if binary is None]
        if missing:
            result.update(status="unavailable", error={"code": "missing_engine",
                          "message": "Unavailable: " + ", ".join(missing)
                          + ". Install FFmpeg locally or supply --ffmpeg/--ffprobe paths."})
            return result
        media = Path(path).resolve(strict=True)
        if not media.is_file():
            raise ValueError("input must be a file")
        info = json.loads(_run([
            resolved["ffprobe"], "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=channels,channel_layout,sample_rate",
            "-of", "json", str(media)], timeout).stdout)
        streams = info.get("streams", [])
        if not streams:
            raise ValueError("input has no audio stream")
        stream = streams[0]
        channels = int(stream["channels"])
        if not 1 <= channels <= 32:
            raise ValueError("only 1..32 channels are supported")
        capacity = min(int(max_seconds * ANALYSIS_RATE),
                       MAX_PCM_BYTES // (4 * channels))
        raw = _run([
            resolved["ffmpeg"], "-v", "error", "-nostdin", "-i", str(media),
            "-map", "0:a:0", "-t", f"{(capacity + 1) / ANALYSIS_RATE:.9f}",
            "-ar", str(ANALYSIS_RATE), "-c:a", "pcm_f32le", "-f", "f32le", "pipe:1"
        ], timeout).stdout
        samples = array("f")
        samples.frombytes(raw)
        del raw
        if sys.byteorder != "little":
            samples.byteswap()
        count = len(samples) // channels
        if count > capacity:
            raise ValueError("decoded input exceeds max_seconds or PCM memory limit")
        if not count or len(samples) % channels:
            raise ValueError("empty or incomplete decoded audio")
        if not all(math.isfinite(x) for x in samples):
            raise ValueError("decoded audio contains nonfinite samples")
        duration = count / ANALYSIS_RATE
        threshold = 10 ** (silence_db / 20)
        pcm = [samples[i::channels] for i in range(channels)]
        del samples
        measured_channels = []
        for i, data in enumerate(pcm):
            first = next((j for j, x in enumerate(data) if abs(x) > threshold), None)
            last = next((count - 1 - j for j, x in enumerate(reversed(data))
                         if abs(x) > threshold), None)
            peak = max(abs(x) for x in data)
            measured_channels.append({
                "channel": i, "onset_seconds": first / ANALYSIS_RATE if first is not None else None,
                "last_active_seconds": last / ANALYSIS_RATE if last is not None else None,
                "peak_dbfs": _db(peak), "rms_dbfs": _db(_rms(data)),
                "full_scale_samples": sum(abs(x) >= 1 for x in data)})
        loudnorm = _run([
            resolved["ffmpeg"], "-hide_banner", "-nostdin", "-i", str(media),
            "-map", "0:a:0", "-af", "loudnorm=print_format=json", "-f", "null", "-"
        ], timeout).stderr.decode("utf-8", errors="replace")
        matches = re.findall(r'\{\s*"input_i"\s*:.*?\}', loudnorm, re.DOTALL)
        if not matches:
            raise ValueError("FFmpeg loudnorm did not emit input measurements")
        stats = json.loads(matches[-1])
        loudness = {"integrated_lufs": _finite_stat(stats["input_i"]),
                    "true_peak_dbtp": _finite_stat(stats["input_tp"]),
                    "range_lu": _finite_stat(stats["input_lra"]),
                    "threshold_lufs": _finite_stat(stats["input_thresh"]),
                    "method": "ffmpeg loudnorm input statistics"}
        result["measurements"] = {
            "duration_seconds": duration, "analysis_sample_rate": ANALYSIS_RATE,
            "source_sample_rate": int(stream["sample_rate"]), "channel_count": channels,
            "channel_layout": stream.get("channel_layout"), "silence_dbfs": silence_db,
            "channels": measured_channels, "loudness": loudness, "cues": []}

        def check(name, passed, actual, expected):
            result["checks"].append({"name": name, "passed": bool(passed),
                                     "actual": actual, "expected": expected})

        if "channels" in expect:
            check("channel_count", channels == expect["channels"], channels, expect["channels"])
        if "duration" in expect:
            tolerance = expect.get("duration_tolerance", 0.01)
            check("duration", abs(duration - expect["duration"]) <= tolerance,
                  duration, {"seconds": expect["duration"], "tolerance": tolerance})
        if "onsets" in expect:
            check("onset_channel_count", len(expect["onsets"]) == channels,
                  channels, len(expect["onsets"]))
            for i, wanted in enumerate(expect["onsets"]):
                actual = measured_channels[i]["onset_seconds"] if i < channels else None
                tolerance = expect.get("onset_tolerance", 0.01)
                passed = (i < channels and (actual is None if wanted is None else
                          actual is not None and abs(actual - wanted) <= tolerance))
                check(f"channel[{i}].onset", passed, actual,
                      {"seconds": wanted, "tolerance": tolerance})
        wanted_loudness = expect.get("loudness", {})
        if "target_lufs" in wanted_loudness:
            actual = loudness["integrated_lufs"]
            target = wanted_loudness["target_lufs"]
            tolerance = wanted_loudness.get("tolerance_lu", 1.0)
            check("integrated_loudness", actual is not None and abs(actual - target) <= tolerance,
                  actual, {"target_lufs": target, "tolerance_lu": tolerance})
        if "max_true_peak_dbtp" in wanted_loudness:
            actual = loudness["true_peak_dbtp"]
            maximum = wanted_loudness["max_true_peak_dbtp"]
            check("true_peak", actual is None or actual <= maximum, actual, {"maximum": maximum})
        for index, cue in enumerate(expect.get("cues", [])):
            name = f"cue[{index}]"
            start, length = float(cue["start"]), float(cue["duration"])
            fi, fo = cue.get("fade_in", 0.0), cue.get("fade_out", 0.0)
            post = cue.get("post_silence", 0.0)
            check(name + ".fade_bounds", fi + fo <= length + 1e-12,
                  {"fade_in": fi, "fade_out": fo, "fade_out_start": length - fo},
                  {"duration": length, "disjoint": True})
            in_range = start + length <= duration + 0.5 / ANALYSIS_RATE
            check(name + ".timeline_bounds", in_range, start + length, {"maximum": duration})
            if post > 0:
                check(name + ".post_window_bounds", start + length + post <= duration,
                      start + length + post, {"maximum": duration})
            indices = cue.get("channels", list(range(channels)))
            check(name + ".channels", all(i < channels for i in indices), indices,
                  {"maximum_index": channels - 1})
            for i in indices:
                if i >= channels or not in_range:
                    continue
                lo, hi = round(start * ANALYSIS_RATE), round((start + length) * ANALYSIS_RATE)
                data = pcm[i][lo:hi]
                # Shorter than ten samples cannot supply ten envelope windows.
                if len(data) < 10:
                    raise ValueError("cue must span at least ten analysis samples")
                reference = max(_rms(data[k * len(data) // 10:(k + 1) * len(data) // 10])
                                for k in range(10))
                tail_samples = max(1, round(min(length * 0.1, fo * 0.2) * ANALYSIS_RATE))
                tail = _rms(data[-tail_samples:])
                ratio = tail / reference if reference > 0 else None
                result["measurements"]["cues"].append({
                    "id": cue.get("id", index), "channel": i,
                    "reference_rms_dbfs": _db(reference), "tail_rms_dbfs": _db(tail),
                    "tail_window_seconds": tail_samples / ANALYSIS_RATE, "tail_ratio": ratio})
                check(f"{name}.channel[{i}].audible", reference > threshold,
                      _db(reference), {"above_dbfs": silence_db})
                if fo > 0:
                    maximum = cue.get("max_tail_ratio", 0.3)
                    check(f"{name}.channel[{i}].tail", ratio is not None and ratio <= maximum,
                          ratio, {"maximum_ratio": maximum})
                if post > 0:
                    post_end = round((start + length + post) * ANALYSIS_RATE)
                    after = pcm[i][hi:post_end]
                    peak = max((abs(x) for x in after), default=0.0)
                    check(f"{name}.channel[{i}].post_silence", peak <= threshold,
                          _db(peak), {"maximum_dbfs": silence_db})
        result["status"] = "succeeded" if all(c["passed"] for c in result["checks"]) else "failed"
    except subprocess.TimeoutExpired:
        result.update(status="timed_out", error={"code": "timeout", "message":
                      "FFmpeg/ffprobe exceeded timeout; child process was stopped."})
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        result["error"] = {"code": "invalid_input_or_engine_output", "message": str(exc)}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--expect", type=Path, help="optional expectations JSON, see module help")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--silence-db", type=float, default=-60.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args(argv)
    try:
        expect = json.loads(args.expect.read_text(encoding="utf-8-sig")) if args.expect else None
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": {"code": "invalid_expectations", "message": str(exc)}}))
        return 2
    result = probe_audio(args.audio, expect, ffmpeg=args.ffmpeg, ffprobe=args.ffprobe,
                         silence_db=args.silence_db, timeout=args.timeout, max_seconds=args.max_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if result["status"] == "unavailable":
        return 3
    if result["status"] == "timed_out":
        return 4
    return 2 if result["error"] else (0 if result["status"] == "succeeded" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
