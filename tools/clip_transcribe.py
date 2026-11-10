"""Transcribe a clip with an explicit engine; the default is local WhisperX.

  python -B tools/clip_transcribe.py clip.mp4 --engine whisperx --model small --language vi
  python -B tools/clip_transcribe.py clip.mp4 --engine whisperx --python D:/env/Scripts/python.exe
  python -B tools/clip_transcribe.py clip.mp4 --engine google

Local mode delegates to caption_align.py in a bounded process, optionally in a
separate environment. It returns aligned {text,start,end} words and NEVER falls
back to Google. Missing/broken engines return JSON status=unavailable, exit 3.
Use caption_align.py --setup-command for installation instructions. Nothing is
installed here. The multilingual default model is small, language explicitly vi.
--transcript supplies spoken text/segments to the local alignment adapter; use
captions.py for corrected display text rather than replacing spoken tokens.

transcribe(clip, ...) retains the Python list result; failures raise exceptions.
transcribe_result(clip, ...) returns a structured status. Google dependencies and
credentials are loaded only for engine='google'. CLI writes a transcript array
only on success, refuses existing sidecars unless --force, and prints JSON status.
All caches default to D:/agent-cache/K-CAP-WIRE/models; no API keys are needed for
local mode. Select another persistent D: cache for production use.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys

DEFAULT_CACHE = Path("D:/agent-cache/K-CAP-WIRE/models")
PROMPT = ('Chép lại TOÀN BỘ âm thanh trong clip tiếng Việt này theo từng cụm ngắn (≤ 6 giây), '
          'đúng nguyên văn kể cả nói ngọng/giọng địa phương. Trả về JSON array, mỗi phần tử '
          '{"start": giây, "end": giây, "speaker": mô tả ngắn người nói, "text": lời, '
          '"kind": "hát"|"nói"|"nhạc"|"ồn"}. Đoạn chỉ có nhạc/tiếng ồn cũng ghi '
          '(text mô tả ngắn). Chỉ trả JSON.')


class EngineUnavailable(RuntimeError):
    """An optional local interpreter, engine, dependency or model is missing."""


def _local_words(clip, *, model, language, engine_python, cache_dir, transcript, timeout):
    if language != "vi":
        raise ValueError("The local adapter requires language='vi'")
    if not isinstance(model, str) or not model.strip() or model.lower().rstrip("/\\").endswith(".en"):
        raise ValueError("Choose a multilingual local model such as small or large-v3")
    command = [str(Path(engine_python or sys.executable).resolve()), "-B",
               str(Path(__file__).with_name("caption_align.py").resolve()), str(clip.resolve()),
               "--model", model, "--language", language, "--cache-dir", str(Path(cache_dir).resolve())]
    if transcript is not None:
        command.extend(["--transcript", str(Path(transcript).resolve())])
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   encoding="utf-8", start_new_session=os.name != "nt")
    except (FileNotFoundError, OSError) as exc:
        raise EngineUnavailable(f"Local engine interpreter unavailable: {exc}") from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # Kill the owned Windows venv launcher AND its inference child.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.communicate()
        raise
    try:
        payload = json.loads(stdout)
    except ValueError as exc:
        raise RuntimeError(f"Local adapter returned invalid JSON (exit {process.returncode}): {stderr[-800:]}") from exc
    if isinstance(payload, dict) and payload.get("status") == "unavailable":
        raise EngineUnavailable(payload.get("error", "WhisperX is unavailable"))
    if process.returncode != 0 or not isinstance(payload, list):
        message = payload.get("error", "Invalid aligned words") if isinstance(payload, dict) else stderr[-800:]
        raise RuntimeError(f"Local alignment failed (exit {process.returncode}): {message}")
    if __package__:
        from .caption_layout import _validate_words
    else:
        from caption_layout import _validate_words
    return _validate_words(payload)


def _google_segments(clip, timeout):
    # This branch is reachable only when the caller explicitly selects Google.
    import base64
    import re
    import requests
    if __package__:
        from .gcp import token_and_project, config
    else:
        from gcp import token_and_project, config
    model = config().get("transcribe_model", "gemini-2.5-flash")
    mp3 = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(clip), "-vn", "-ac", "1",
                          "-ar", "16000", "-b:a", "48k", "-f", "mp3", "-"],
                         capture_output=True, check=True, timeout=timeout).stdout
    token, project = token_and_project()
    url = f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/global/publishers/google/models/{model}:generateContent"
    response = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=timeout, json={
        "contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": "audio/mp3",
                      "data": base64.b64encode(mp3).decode()}}, {"text": PROMPT}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}})
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(re.sub(r"^```(?:json)?|```$", "", text.strip()))


def transcribe(clip, *, engine="google", model="small", language="vi",
               engine_python=None, cache_dir=DEFAULT_CACHE, transcript=None, timeout=600):
    """Return a list. Default Google (WhisperX is opt-in: engine="whisperx"; blocked on this machine by Application Control)."""
    if engine not in {"whisperx", "google"}:
        raise ValueError("engine must be whisperx or google")
    if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive finite seconds")
    clip = Path(clip)
    if not clip.is_file():
        raise ValueError(f"Clip does not exist: {clip}")
    if engine == "whisperx":
        return _local_words(clip, model=model, language=language, engine_python=engine_python,
                            cache_dir=cache_dir, transcript=transcript, timeout=timeout)
    if engine_python is not None or transcript is not None:
        raise ValueError("engine_python and transcript are local-only options")
    return _google_segments(clip, timeout)


def transcribe_result(clip, **options):
    """Structured success/unavailable/error result, with no fallback on failure."""
    engine = options.get("engine", "google")
    try:
        segments = transcribe(clip, **options)
        return {"status": "ok", "engine": engine, "timing": "aligned" if engine == "whisperx" else "estimated",
                "segments": segments, "words": segments if engine == "whisperx" else []}
    except EngineUnavailable as exc:
        return {"status": "unavailable", "engine": engine, "error": str(exc),
                "hint": "Run tools/caption_align.py --setup-command; select a working separate D: "
                        "environment with --python. No Google fallback was attempted."}
    except KeyboardInterrupt:
        return {"status": "cancelled", "engine": engine, "error": "Transcription cancelled"}
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "engine": engine, "error": str(exc)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("clips", nargs="+", type=Path)
    parser.add_argument("--engine", choices=["whisperx", "google"], default="whisperx")
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", choices=["vi"], default="vi")
    parser.add_argument("--python", dest="engine_python", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--output", type=Path, help="Transcript array output, for a single clip")
    parser.add_argument("--force", action="store_true", help="Explicitly replace an existing transcript output")
    args = parser.parse_args(argv)
    if len(args.clips) != 1 and (args.output or args.transcript):
        parser.error("--output and --transcript require exactly one clip")
    exit_code = 0
    for clip in args.clips:
        output = args.output or clip.with_suffix(".transcript.json")
        try:
            if output.resolve() in {clip.resolve(), args.transcript.resolve() if args.transcript else None}:
                raise ValueError("Output must differ from clip and transcript input")
            if output.exists() and not args.force:
                raise ValueError(f"Refusing to overwrite {output}; use --force explicitly")
            result = transcribe_result(clip, engine=args.engine, model=args.model, language=args.language,
                                       engine_python=args.engine_python, cache_dir=args.cache_dir,
                                       transcript=args.transcript, timeout=args.timeout)
            if result["status"] == "ok":
                with output.open("w" if args.force else "x", encoding="utf-8") as stream:
                    json.dump(result["segments"], stream, ensure_ascii=False, indent=2, allow_nan=False)
                    stream.write("\n")
                result["output"] = str(output.resolve())
        except (OSError, ValueError) as exc:
            result = {"status": "error", "engine": args.engine, "error": str(exc)}
        result["clip"] = str(clip)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        exit_code = max(exit_code, {"ok": 0, "error": 2, "unavailable": 3, "cancelled": 130}[result["status"]])
        if result["status"] == "cancelled":
            break
    return exit_code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
