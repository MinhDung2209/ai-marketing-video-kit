"""Caption-first source transcripts, with conservative rolling-WebVTT deduplication.

Examples (stdout is always one JSON result)::

    python tools/source_captions.py captions.vi.vtt
    python tools/source_captions.py clip.mp4 --language vi
    python tools/source_captions.py https://example/video --cache-dir D:/agent-cache/captions
    python tools/source_captions.py https://example/video --captions corrected.vtt

Local sidecars work with the standard library alone. URL acquisition requires an
already installed yt-dlp, or --yt-dlp pointing to one; nothing is installed or
transcribed automatically. Missing captions return status="asr_required" and an
explicit local-ASR request. Acquisition failures return error/unavailable instead.

Only a suffix/prefix shared by temporally overlapping, same-speaker cues is
collapsed. Adjacent or separated repeats and repeats inside a cue survive.
Use --keep-repeats for authored overlapping dialogue whose repetition cannot be
distinguished from a rolling display. Deduplication never changes the sidecar:
raw captions, every cue's markup, IDs, settings and source times remain in JSON.
Segment times are source cue bounds, NOT estimated or aligned word timings.

Pattern reference: iankiku/anytranscript, src/{vtt,transcribe,ytdlp}.ts,
research snapshot 934d30fa52c7efadeed04a66db0858680c3f9876 (MIT).
This implementation adds temporal/speaker guards rather than globally dropping
repeated lines. It does not depend on anytranscript or a Node runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Sequence
from urllib.parse import urlparse


_STAMP = r"(?:\d{2,}:)?\d{2}:\d{2}[.,]\d{3}"
_TIMING = re.compile(rf"^({_STAMP})\s+-->\s+({_STAMP})(?:\s+(.*))?$")
_TAG = re.compile(r"<[^>]*>")
_VOICE = re.compile(r"<v(?:\.[^\s>]+)*\s+([^>]+)>")


def _seconds(stamp: str) -> float:
    parts = stamp.replace(",", ".").split(":")
    if not 0 <= float(parts[-1]) < 60 or not 0 <= int(parts[-2]) < 60:
        raise ValueError(f"Invalid caption timestamp: {stamp}")
    return round(sum(float(part) * 60 ** i for i, part in enumerate(reversed(parts))), 3)


def parse_vtt(text: str) -> list[dict[str, Any]]:
    """Read WebVTT (also SRT timing blocks), retaining original cue text/timing.

    Malformed or backwards cues raise ValueError, never masquerade as missing
    captions. Header-only/empty sidecars are valid but have no spoken captions.
    """
    cues: list[dict[str, Any]] = []
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    for block in re.split(r"\n[ \t]*\n", normalized):
        lines = block.strip("\n").split("\n")
        if not lines or not lines[0].strip():
            continue
        first = lines[0].strip()
        if (first == "WEBVTT" or first.startswith(("WEBVTT ", "WEBVTT\t"))
                or first in {"STYLE", "REGION", "NOTE"}
                or first.startswith(("NOTE ", "NOTE\t"))):
            continue
        timing_index = 0 if "-->" in lines[0] else 1
        if len(lines) <= timing_index:
            raise ValueError(f"Caption block has no timing: {first!r}")
        timing = _TIMING.fullmatch(lines[timing_index].strip())
        if not timing:
            raise ValueError(f"Invalid caption timing: {lines[timing_index]!r}")
        start, end = _seconds(timing[1]), _seconds(timing[2])
        if end <= start:
            raise ValueError("Caption end must be greater than start")
        if cues and start < cues[-1]["start"]:
            raise ValueError("Caption start times must be ordered")
        raw_text = "\n".join(lines[timing_index + 1:])
        cues.append({
            "index": len(cues),
            "id": lines[0] if timing_index else None,
            "start": start, "end": end,
            "start_timestamp": timing[1], "end_timestamp": timing[2],
            "settings": timing[3] or "", "raw_timing": lines[timing_index],
            "raw_text": raw_text,
            "text": " ".join(html.unescape(_TAG.sub("", raw_text)).split()),
            "speakers": [html.unescape(s) for s in _VOICE.findall(raw_text)],
        })
    return cues


def deduplicate_cues(cues: Sequence[dict[str, Any]], *, enabled: bool = True
                     ) -> list[dict[str, Any]]:
    """Emit novel text; retain cue bounds and references for all matched tokens.

    Exact, case-sensitive Unicode tokens are compared. No semantic matching,
    accent removal or global text set is used. Dropped display tokens extend the
    display bounds of their originating segment; source cue bounds stay intact
    in cues[]. Prefix matching uses the previous cue, not unrelated old text.
    """
    segments: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    previous_tokens: list[str] = []
    previous_owners: list[int] = []
    for cue in cues:
        tokens = cue["text"].split()
        overlap = 0
        if (enabled and previous is not None
                and cue["start"] < previous["end"]
                and cue["speakers"] == previous["speakers"]):
            for size in range(min(len(tokens), len(previous_tokens)), 0, -1):
                if previous_tokens[-size:] == tokens[:size]:
                    overlap = size
                    break
        owners = previous_owners[-overlap:] if overlap else []
        for owner in set(owners):
            segment = segments[owner]
            segment["end"] = max(segment["end"], cue["end"])
            if cue["index"] not in segment["source_cues"]:
                segment["source_cues"].append(cue["index"])
        if overlap < len(tokens):
            owner = len(segments)
            segments.append({
                "start": cue["start"], "end": cue["end"],
                "text": " ".join(tokens[overlap:]),
                "source_cues": [cue["index"]],
                "deduplicated_prefix_tokens": overlap,
                "timing": "source_cue_bounds",
            })
            owners.extend([owner] * (len(tokens) - overlap))
        previous, previous_tokens, previous_owners = cue, tokens, owners
    return segments


def _result(status: str, source_reference: str, language: str, message: str,
            **extra: Any) -> dict[str, Any]:
    return {"schema_version": 1, "status": status, "source": None,
            "language": language, "text": "", "segments": [], "cues": [],
            "provenance": {"source": source_reference}, "message": message,
            "requires_asr": status == "asr_required", **extra}


def _missing(source: str, language: str, reason: str, **extra: Any) -> dict[str, Any]:
    return _result("asr_required", source, language, reason, asr_request={
        "action": "transcribe_with_explicit_local_engine",
        "source": source, "language": language,
        "instruction": "Select an installed local ASR engine and multilingual model "
                       "explicitly (for Vietnamese use language vi). No ASR was run.",
    }, **extra)


def _read_captions(path: Path, source: str, language: str, *,
                   deduplicate: bool, provenance: dict[str, Any] | None = None
                   ) -> dict[str, Any]:
    data = path.read_bytes()
    text = data.decode("utf-8-sig")
    cues = parse_vtt(text)
    details = {"source": source, "caption_path": str(path.resolve()),
               "sha256": hashlib.sha256(data).hexdigest(), "byte_size": len(data),
               "raw_captions": data.decode("utf-8"),
               "deduplication": "overlapping_suffix_prefix" if deduplicate else "disabled",
               **(provenance or {})}
    segments = deduplicate_cues(cues, enabled=deduplicate)
    if not segments:
        return _missing(source, language, "Caption track contains no spoken text.",
                        provenance=details, cues=cues)
    return _result("ok", source, language, "Existing captions acquired; no ASR run.",
                   source="captions", text=" ".join(s["text"] for s in segments),
                   segments=segments, cues=cues, provenance=details)


def _resolve_ytdlp(command: Sequence[str] | None) -> list[str] | None:
    if command is not None:
        if not command:
            raise ValueError("yt-dlp command must not be empty")
        if not shutil.which(str(command[0])) and not Path(command[0]).is_file():
            return None
        return [str(part) for part in command]
    if binary := shutil.which("yt-dlp"):
        return [binary]
    if importlib.util.find_spec("yt_dlp") is not None:
        return [sys.executable, "-m", "yt_dlp"]
    return None


def _run(command: list[str], args: list[str], timeout: float) -> str:
    completed = subprocess.run(command + args, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout,
                               check=False, shell=False)
    if completed.returncode:
        raise RuntimeError(f"yt-dlp exited {completed.returncode}: "
                           f"{completed.stderr.strip()[-1500:]}")
    return completed.stdout


def _select_track(info: dict[str, Any], language: str
                  ) -> tuple[str, str, list[dict[str, Any]]] | None:
    candidates = [language] if language.endswith("-orig") else [language + "-orig", language]
    # Prefer human captions to generated tracks, then original language to translation.
    for key, kind in (("subtitles", "manual"), ("automatic_captions", "automatic")):
        tracks = info.get(key) or {}
        for candidate in candidates:
            if tracks.get(candidate):
                return kind, candidate, tracks[candidate]
    return None


def acquire_captions(source: str | Path, *, captions: str | Path | None = None,
                     language: str = "vi", cache_dir: str | Path | None = None,
                     ytdlp_command: Sequence[str] | None = None,
                     timeout: float = 60, deduplicate: bool = True) -> dict[str, Any]:
    """Acquire local/URL captions, returning a JSON-serializable result.

    URL mode uses yt-dlp metadata followed by a caption-only download into an
    isolated temporary child of caller-supplied cache_dir. That child is removed
    on success, failure and timeout. No media, cookies, models or API keys are
    accessed. timeout is per subprocess, at most two subprocesses per request.
    Raw downloaded captions are embedded in provenance before cleanup.
    """
    source = str(source)
    try:
        if not language or not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", language):
            raise ValueError("Use one explicit language code, e.g. vi, en, or vi-orig")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        if captions is not None:
            return _read_captions(Path(captions), source, language,
                                  deduplicate=deduplicate, provenance={"kind": "local_override"})
        parsed = urlparse(source)
        is_url = parsed.scheme.lower() in {"https", "http"} and bool(parsed.netloc)
        if not is_url:
            media = Path(source)
            if not media.is_file():
                raise ValueError(f"Source does not exist: {source}")
            if media.suffix.lower() in {".vtt", ".srt"}:
                return _read_captions(media, source, language, deduplicate=deduplicate,
                                      provenance={"kind": "local"})
            for suffix in (f".{language}-orig.vtt", f".{language}.vtt", ".vtt",
                           f".{language}.srt", ".srt"):
                sidecar = media.with_suffix(suffix)
                if sidecar.is_file():
                    return _read_captions(sidecar, source, language, deduplicate=deduplicate,
                                          provenance={"kind": "local_sidecar"})
            return _missing(source, language, "No matching local caption sidecar; local ASR required.")

        command = _resolve_ytdlp(ytdlp_command)
        if command is None:
            return _result("unavailable", source, language,
                           "yt-dlp is unavailable. Supply --captions, an installed --yt-dlp "
                           "executable, or install yt-dlp in a separate D:/ environment. "
                           "Caption availability is unknown; no ASR was run.")
        if cache_dir is None:
            raise ValueError("URL acquisition requires an explicit --cache-dir")
        base = ["--ignore-config", "--no-cache-dir", "--no-playlist", "--no-warnings",
                "--encoding", "utf-8",
                "--no-progress", "--socket-timeout", str(timeout), "--retries", "0",
                "--extractor-retries", "0"]
        info = json.loads(_run(command, base + ["--skip-download", "--dump-single-json",
                                               "--", source], timeout))
        if not isinstance(info, dict) or info.get("_type") in {"playlist", "multi_video"}:
            raise ValueError("Expected metadata for one video")
        metadata = {key: info.get(key) for key in
                    ("id", "title", "uploader", "duration", "webpage_url", "extractor")}
        track = _select_track(info, language)
        if track is None:
            return _missing(source, language, "No captions for requested language; local ASR required.",
                            provenance={"source": source, "media": metadata})
        kind, track_language, formats = track
        if not any(f.get("ext") in {"vtt", "srt"} for f in formats):
            raise ValueError("Caption track exists but has no supported VTT/SRT format")
        cache = Path(cache_dir).resolve()
        cache.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="source-captions-", dir=cache) as temporary:
            workspace = Path(temporary)
            args = base + ["--skip-download", "--no-write-info-json", "--no-write-thumbnail",
                           "--write-subs" if kind == "manual" else "--write-auto-subs",
                           "--no-write-auto-subs" if kind == "manual" else "--no-write-subs",
                           "--sub-langs", re.escape(track_language), "--sub-format", "vtt/srt",
                           "--output", str(workspace).replace("%", "%%") + "/captions.%(ext)s",
                           "--", source]
            _run(command, args, timeout)
            files = sorted(p for p in workspace.iterdir() if p.suffix in {".vtt", ".srt"})
            if len(files) != 1:
                raise ValueError("Caption download did not produce exactly one sidecar")
            return _read_captions(files[0], source, track_language, deduplicate=deduplicate,
                                  provenance={"kind": kind, "requested_language": language,
                                              "media": metadata, "backend": "yt-dlp",
                                              "caption_path_is_temporary": True})
    except subprocess.TimeoutExpired:
        return _result("error", source, language, f"yt-dlp timed out after {timeout}s; no ASR was run.")
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as exc:
        return _result("error", source, language, str(exc))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="Local VTT/SRT/media path or one HTTP(S) video URL")
    parser.add_argument("--captions", help="Use this existing sidecar first (including corrected text)")
    parser.add_argument("--language", default="vi")
    parser.add_argument("--cache-dir", help="Required in URL mode; caller-owned temporary parent")
    parser.add_argument("--yt-dlp", dest="ytdlp", help="Already installed optional executable")
    parser.add_argument("--timeout", type=float, default=60, help="Seconds per yt-dlp subprocess")
    parser.add_argument("--keep-repeats", action="store_true", help="Disable rolling deduplication")
    args = parser.parse_args(argv)
    result = acquire_captions(args.source, captions=args.captions, language=args.language,
                              cache_dir=args.cache_dir,
                              ytdlp_command=[args.ytdlp] if args.ytdlp else None,
                              timeout=args.timeout, deduplicate=not args.keep_repeats)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"ok": 0, "asr_required": 2, "unavailable": 3, "error": 1}[result["status"]]


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
