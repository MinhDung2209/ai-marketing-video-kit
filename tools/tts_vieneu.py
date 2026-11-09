"""Optional local VieNeu v3 Turbo preset narration (CPU/ONNX, 48 kHz).

Usage: python -B tools/tts_vieneu.py voice.json NEW_OUTPUT --voice "Ngọc Lan"
Run using a separate VieNeu environment's Python if desired; the kit needs no
new dependencies. --check tests imports only; --list-voices loads the engine.
Weights must already be cached unless --allow-download is explicitly supplied.
Downloads are public model assets, never hosted speech inference. All library
caches/temp files are redirected to --cache-dir before importing the engine.

Input follows tts_script.py: lines [{id,text,caption?}, {id,pause,caption?}],
gap_seconds (default .35). Optional spoken_text overrides pronunciation while
timing retains original text/caption, e.g. text="AI tăng 25%", spoken_text=
"ây ai tăng hai mươi lăm phần trăm". Otherwise raw numbers/acronyms go to
VieNeu's own normalizer. No automatic acronym guessing is performed here.
Profile/direction are not supported by preset synthesis. Replace legacy English
bracket cues with spoken_text or VieNeu cues such as [cười].

Output: one PCM WAV per spoken line, narration.wav, and the existing timing.json
shape {model,voice,total,lines:[{id,file,start,dur,text,caption?,pause?}]}.
Durations are probed from decoded WAV frames, never estimated from text. There
is .3s leading silence, the configured gap after each line, and 1s trailing
silence, matching tts_script.py. A fresh output directory is required so reruns
cannot replace approved audio. Publication happens only after all lines pass.
Stdout is one JSON result: status ok/unavailable/error; exit codes 0/3/2.
--check success means importable, not that weights or speech quality are tested.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
import importlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import wave


MODEL = "vieneu-v3turbo"
DEFAULT_CACHE = Path("D:/agent-cache/K-TTS-VI/models")
SAMPLE_RATE = 48_000
HINT = ("Use a separate VieNeu v3 Turbo Python environment on D:/ and run this "
        "adapter with that Python. Provision its optional ONNX dependencies and "
        "public weights into --cache-dir; --allow-download permits model downloads. "
        "No hosted engine is used.")


class EngineUnavailable(RuntimeError):
    """Optional engine, native dependencies, or local weights are absent."""


def _seconds(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number of seconds")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError(f"{label} must be finite and {'positive' if positive else 'nonnegative'}")
    return result


def validate_script(script: object) -> tuple[list[dict], float, list[str]]:
    """Validate all input before loading models or creating any output."""
    if not isinstance(script, dict) or not isinstance(script.get("lines"), list) or not script["lines"]:
        raise ValueError("Script needs a nonempty lines array")
    gap = _seconds(script.get("gap_seconds", .35), "gap_seconds")
    seen = set()
    lines = []
    warnings = []
    if script.get("profile") or any(isinstance(x, dict) and x.get("direction") for x in script["lines"]):
        warnings.append("Preset synthesis ignores profile and direction; listen to the generated speech.")
    reserved = {"con", "prn", "aux", "nul", "narration", "timing"}
    reserved.update(f"{prefix}{n}" for prefix in ("com", "lpt") for n in range(1, 10))
    for index, line in enumerate(script["lines"]):
        if not isinstance(line, dict):
            raise ValueError(f"Line {index} must be an object")
        ident = line.get("id")
        if (not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", ident)
                or ident.casefold() in seen or ident.casefold() in reserved):
            raise ValueError(f"Line {index} needs a unique, safe filename id (case-insensitive)")
        seen.add(ident.casefold())
        if "caption" in line and not isinstance(line["caption"], str):
            raise ValueError(f"{ident}: caption must be a string")
        if "pause" in line:
            _seconds(line["pause"], f"{ident}.pause", positive=True)
            if line.get("text") or "spoken_text" in line:
                raise ValueError(f"{ident}: a pause line cannot also contain speech")
        else:
            for key in ("text", "spoken_text") if "spoken_text" in line else ("text",):
                if not isinstance(line.get(key), str) or not line[key].strip():
                    raise ValueError(f"{ident}: {key} must be nonempty text")
            spoken = line.get("spoken_text", line["text"])
            if re.search(r"\[[a-zA-Z]+(?: [a-zA-Z]+)*\]", spoken):
                raise ValueError(f"{ident}: legacy English bracket cues are unsupported; supply spoken_text")
        lines.append(dict(line))
    return lines, gap, warnings


@contextmanager
def _engine_environment(cache_dir: str | Path, allow_download: bool):
    """Keep optional libraries' caches/temp on the caller's chosen drive."""
    cache = Path(cache_dir).resolve()
    folders = {"HF_HOME": "huggingface", "HF_HUB_CACHE": "huggingface/hub",
               "HUGGINGFACE_HUB_CACHE": "huggingface/hub", "TORCH_HOME": "torch",
               "XDG_CACHE_HOME": "xdg", "NUMBA_CACHE_DIR": "numba",
               "MPLCONFIGDIR": "matplotlib", "TEMP": "tmp", "TMP": "tmp",
               "TMPDIR": "tmp"}
    values = {key: str(cache / folder) for key, folder in folders.items()}
    values.update(HF_HUB_OFFLINE="0" if allow_download else "1",
                  TRANSFORMERS_OFFLINE="0" if allow_download else "1",
                  HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1")
    previous = {key: os.environ.get(key) for key in values}
    previous_tempdir = tempfile.tempdir
    try:
        for folder in set(folders.values()):
            (cache / folder).mkdir(parents=True, exist_ok=True)
        os.environ.update(values)
        tempfile.tempdir = values["TEMP"]
        yield
    finally:
        tempfile.tempdir = previous_tempdir
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _factory():
    try:
        return importlib.import_module("vieneu").Vieneu
    except Exception as exc:
        # Optional native packages can raise RuntimeError (DLL/ABI failures)
        # during import, as well as the usual ImportError/OSError.
        raise EngineUnavailable(f"VieNeu v3 Turbo is unavailable: {exc}") from exc


def _load_engine():
    factory = _factory()
    try:
        # Explicit local implementation: never factory defaults, remote/API, or v4.
        return factory(mode="v3turbo", device="cpu", backend="onnx")
    except Exception as exc:
        raise EngineUnavailable(f"VieNeu v3 Turbo dependencies/weights unavailable: {exc}") from exc


def probe_wav(path: str | Path) -> int:
    """Probe actual PCM frame count, rejecting empty/truncated/unexpected output."""
    with wave.open(str(path), "rb") as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"{path}: expected 48 kHz mono PCM16 WAV from v3 Turbo")
        count = 0
        while block := audio.readframes(65_536):
            count += len(block)
        if count == 0 or count != audio.getnframes() * 2:
            raise ValueError(f"{path}: empty or truncated WAV")
        return audio.getnframes()


def _silence(output, frames: int) -> None:
    while frames:
        chunk = min(frames, 65_536)
        output.writeframesraw(b"\x00\x00" * chunk)
        frames -= chunk


def synthesize(script: object, out: str | Path, *, voice: str,
               cache_dir: str | Path = DEFAULT_CACHE, allow_download: bool = False) -> dict:
    """Generate into a fresh directory; errors leave no published partial audio."""
    lines, gap, warnings = validate_script(script)
    if not isinstance(voice, str) or not voice.strip():
        raise ValueError("Select an explicit preset with --voice (see --list-voices)")
    out = Path(out).resolve()
    if out.exists():
        raise ValueError(f"Output already exists; choose a fresh directory: {out}")
    engine = None
    with _engine_environment(cache_dir, allow_download), redirect_stdout(sys.stderr):
        try:
            if any("pause" not in line for line in lines):
                engine = _load_engine()
                # Resolve before inference so an unknown preset cannot silently use a default.
                engine.get_preset_voice(voice)
            out.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".vieneu-", dir=out.parent) as temporary:
                stage = Path(temporary) / "audio"
                stage.mkdir()
                meta = []
                cursor = round(.3 * SAMPLE_RATE)
                gap_frames = round(gap * SAMPLE_RATE)
                for line in lines:
                    item = {"id": line["id"], "start": round(cursor / SAMPLE_RATE, 6)}
                    if "caption" in line:
                        item["caption"] = line["caption"]
                    if "pause" in line:
                        frames = round(line["pause"] * SAMPLE_RATE)
                        if frames < 1:
                            raise ValueError(f"{line['id']}: pause is shorter than one sample")
                        item.update(file=None, text="", pause=True)
                    else:
                        filename = f"{line['id']}.wav"
                        audio = engine.infer(line.get("spoken_text", line["text"]), voice=voice)
                        engine.save(audio, str(stage / filename))
                        frames = probe_wav(stage / filename)
                        item.update(file=filename, text=line["text"])
                    item["dur"] = round(frames / SAMPLE_RATE, 6)
                    meta.append(item)
                    cursor += frames + gap_frames
                total_frames = cursor + SAMPLE_RATE
                timing = {"model": MODEL, "voice": voice, "total": round(total_frames / SAMPLE_RATE, 6),
                          "lines": meta}
                with wave.open(str(stage / "narration.wav"), "wb") as output:
                    output.setparams((1, 2, SAMPLE_RATE, 0, "NONE", "not compressed"))
                    written = 0
                    for item in meta:
                        start = round(item["start"] * SAMPLE_RATE)
                        _silence(output, start - written)
                        if item["file"]:
                            with wave.open(str(stage / item["file"]), "rb") as source:
                                while block := source.readframes(65_536):
                                    output.writeframesraw(block)
                                written = start + source.getnframes()
                        else:
                            written = start  # Next line or final padding fills this pause.
                    _silence(output, total_frames - written)
                if probe_wav(stage / "narration.wav") != total_frames:
                    raise ValueError("Narration frame count differs from measured timeline")
                (stage / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
                if engine is not None:
                    engine.close()
                    engine = None
                if out.exists():
                    raise ValueError(f"Output appeared during synthesis: {out}")
                stage.rename(out)
        finally:
            if engine is not None:
                engine.close()
    return {"status": "ok", "engine": MODEL, "output": str(out),
            "timing": str(out / "timing.json"), "narration": str(out / "narration.wav"),
            "total": timing["total"], "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", nargs="?")
    parser.add_argument("out", nargs="?")
    parser.add_argument("--voice", help="explicit local v3 Turbo preset name")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--allow-download", action="store_true", help="allow public model asset downloads")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check optional engine import without loading weights")
    mode.add_argument("--list-voices", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check or args.list_voices:
            with _engine_environment(args.cache_dir, args.allow_download), redirect_stdout(sys.stderr):
                if args.check:
                    _factory()
                    result = {"status": "ok", "engine": MODEL, "check": "import_only"}
                else:
                    engine = _load_engine()
                    try:
                        result = {"status": "ok", "engine": MODEL, "voices": engine.list_preset_voices()}
                    finally:
                        engine.close()
        else:
            if not args.script or not args.out or not args.voice:
                raise ValueError("Provide script, a fresh output directory, and --voice; or use --check/--list-voices")
            script = json.loads(Path(args.script).read_text(encoding="utf-8-sig"))
            result = synthesize(script, args.out, voice=args.voice, cache_dir=args.cache_dir,
                                allow_download=args.allow_download)
        code = 0
    except EngineUnavailable as exc:
        result = {"status": "unavailable", "engine": MODEL, "error": str(exc), "hint": HINT}
        code = 3
    except Exception as exc:
        result = {"status": "error", "engine": MODEL, "error": str(exc)}
        code = 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
