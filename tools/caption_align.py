"""Optional local Vietnamese word alignment; no kit dependencies or providers.

Run with the kit Python and --python D:/.../whisperx-env/Scripts/python.exe
to keep Torch/WhisperX separate. --setup-command prints installation commands;
it never installs anything. FFmpeg must be on PATH. Public models download on
first use into --cache-dir; no API key or diarization is used.

Success: JSON array of {text, start, end}, seconds relative to decoded audio.
Failure: JSON {status, engine, error, hint}, exit 3 for unavailable, 2 otherwise.
--transcript accepts UTF-8 text or JSON [{text,start,end}] / {segments: [...]}
and preserves supplied tokens. Without it, multilingual Whisper ASR runs first.
Unalignable/missing/out-of-order words fail instead of receiving estimated times.
This tool does not read or rewrite voice.json or corrected caption sidecars.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys


VI_ALIGN_MODEL = "nguyenvulebinh/wav2vec2-base-vi-vlsp2020"
DEFAULT_CACHE = Path("D:/agent-cache/K-CAP-ALIGN/models")
WHISPERX_VERSION = "3.8.6"


class EngineUnavailable(RuntimeError):
    """The optional engine, native dependency or model is unavailable."""


def setup_command(cache_dir: str | Path = DEFAULT_CACHE) -> str:
    """Return reviewable PowerShell commands for a separate CPU environment."""
    root = Path(cache_dir).resolve().parent
    env_python = root / "whisperx-env/Scripts/python.exe"
    kit_python = Path(__file__).resolve().parents[1] / ".venv/Scripts/python.exe"

    def quote(value: object) -> str:
        return "'" + str(value).replace("'", "''") + "'"

    return "\n".join([
        f"New-Item -ItemType Directory -Force {quote(root / 'tmp')} | Out-Null",
        f"$env:TEMP={quote(root / 'tmp')}; $env:TMP=$env:TEMP",
        f"$env:PIP_CACHE_DIR={quote(root / 'pip-cache')}",
        f"& {quote(kit_python)} -B -m venv {quote(root / 'whisperx-env')}",
        f"& {quote(env_python)} -B -m pip install torch==2.8.0 torchaudio==2.8.0 "
        "torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu",
        f"& {quote(env_python)} -B -m pip install whisperx=={WHISPERX_VERSION} "
        "'transformers>=4.48,<5'",
        "# Windows also needs Microsoft Visual C++ runtime DLLs in the engine environment.",
        "# Then pass --python " + quote(env_python) + " to this adapter.",
    ])


def _configure_cache(cache_dir: str | Path) -> Path:
    cache = Path(cache_dir).resolve()
    # Set these before lazy imports: libraries otherwise write to the user profile.
    for variable, folder in {
        "HF_HOME": "huggingface", "HF_HUB_CACHE": "huggingface/hub",
        "TORCH_HOME": "torch", "XDG_CACHE_HOME": "xdg", "NLTK_DATA": "nltk",
        "NUMBA_CACHE_DIR": "numba", "MPLCONFIGDIR": "matplotlib",
        "TEMP": "tmp", "TMP": "tmp",
    }.items():
        directory = cache / folder
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(directory)
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    return cache


def _seconds(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number of seconds")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _run_engine(command: list[str], timeout: float) -> int:
    process = subprocess.Popen(command, start_new_session=os.name != "nt")
    try:
        return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # Windows venv launchers have a child Python; killing only the launcher
        # leaves inference running. Terminate the owned tree before re-raising.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()
        raise


def _segments(transcript: object, duration: float) -> list[dict]:
    if isinstance(transcript, str):
        transcript = [{"text": transcript, "start": 0.0, "end": duration}]
    if not isinstance(transcript, list) or not transcript:
        raise ValueError("Transcript must contain text or a nonempty segment array")
    result = []
    previous = 0.0
    for index, item in enumerate(transcript):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            raise ValueError(f"Segment {index} requires a text string")
        # WhisperX splits on ASCII spaces; retain token spelling, case and accents.
        text = " ".join(item["text"].split())
        start = _seconds(item.get("start"), f"Segment {index} start")
        end = _seconds(item.get("end"), f"Segment {index} end")
        if not text or not (previous <= start < end <= duration):
            raise ValueError(f"Segment {index} is empty, overlaps or exceeds {duration}s")
        result.append({"text": text, "start": start, "end": end})
        previous = end
    return result


def _words(result: object, segments: list[dict], duration: float) -> list[dict]:
    if not isinstance(result, dict) or not isinstance(result.get("word_segments"), list):
        raise ValueError("WhisperX returned no aligned word array")
    expected = [word for segment in segments for word in segment["text"].split()]
    raw = result["word_segments"]
    if [word.get("word") for word in raw] != expected:
        raise ValueError("Alignment lost or changed transcript tokens; review the transcript")
    words = []
    previous = 0.0
    for index, word in enumerate(raw):
        if "start" not in word or "end" not in word or "score" not in word:
            raise ValueError(f"Unaligned word {index}: {word.get('word')!r}; "
                             "spell numbers/acronyms as spoken or adjust segment bounds")
        start = _seconds(word["start"], f"Word {index} start")
        end = _seconds(word["end"], f"Word {index} end")
        if not (previous <= start < end <= duration):
            raise ValueError(f"Word {index} is overlapping, unordered or outside {duration}s")
        words.append({"text": word["word"], "start": start, "end": end})
        previous = end
    return words


def align(audio_path: str | Path, *, model: str, language: str = "vi",
          align_model: str = VI_ALIGN_MODEL, transcript: object = None,
          cache_dir: str | Path = DEFAULT_CACHE, device: str = "cpu",
          compute_type: str = "int8", batch_size: int = 4) -> list[dict]:
    """Return real aligned words, raising EngineUnavailable or ValueError on failure.

    model is an explicit multilingual Whisper name/path (e.g. small, large-v3).
    It is loaded only when transcript is None. There is no timing interpolation.
    Call in a fresh separate process if other ML libraries are already imported.
    """
    if language != "vi":
        raise ValueError("This Vietnamese adapter requires language='vi'")
    if not model.strip() or model.lower().rstrip("/\\").endswith(".en"):
        raise ValueError("Choose an explicit multilingual Whisper model, e.g. small or large-v3")
    if not align_model.strip() or batch_size < 1:
        raise ValueError("Alignment model must be nonempty and batch_size must be positive")
    audio_path = Path(audio_path).resolve()
    if not audio_path.is_file():
        raise ValueError(f"Audio file does not exist: {audio_path}")
    try:
        # Check availability before creating cache directories.
        whisperx = importlib.import_module("whisperx")
    except (ImportError, OSError) as exc:
        raise EngineUnavailable(f"WhisperX is unavailable in {sys.executable}: {exc}") from exc
    cache = _configure_cache(cache_dir)
    try:
        # Upstream diagnostics must never contaminate the JSON stream.
        with redirect_stdout(sys.stderr):
            audio = whisperx.load_audio(str(audio_path))
            duration = len(audio) / 16000.0
            if duration <= 0:
                raise ValueError("Decoded audio is empty")
            if transcript is None:
                recognizer = whisperx.load_model(
                    model, device, compute_type=compute_type, language="vi",
                    download_root=str(cache / "whisper"), vad_method="silero",
                )
                transcription = recognizer.transcribe(audio, batch_size=batch_size, language="vi")
                transcript = transcription["segments"]
                del recognizer
            segments = _segments(transcript, duration)
            aligner, metadata = whisperx.load_align_model(
                language_code="vi", device=device, model_name=align_model,
                model_dir=str(cache / "huggingface/hub"),
            )
            result = whisperx.align(
                segments, aligner, metadata, audio, device,
                interpolate_method="ignore", return_char_alignments=False,
            )
        return _words(result, segments, duration)
    except (ImportError, OSError) as exc:
        raise EngineUnavailable(f"WhisperX dependency/model is unavailable: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", nargs="?", type=Path)
    parser.add_argument("--model", help="Explicit multilingual Whisper model, e.g. small or large-v3")
    parser.add_argument("--language", choices=["vi"], default="vi")
    parser.add_argument("--align-model", default=VI_ALIGN_MODEL)
    parser.add_argument("--transcript", type=Path, help="UTF-8 .txt or segment .json, preserving spoken tokens")
    parser.add_argument("--python", dest="engine_python", type=Path, help="Python in a separate WhisperX environment")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=600, help="Separate environment process timeout in seconds")
    parser.add_argument("--output", type=Path, help="Optional JSON array file, written only after successful alignment")
    parser.add_argument("--setup-command", action="store_true")
    args = parser.parse_args(argv)
    if args.setup_command:
        print(setup_command(args.cache_dir))
        return 0
    if args.audio is None or not args.model:
        parser.error("audio and --model are required (use --setup-command for installation)")
    try:
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError("--timeout must be a positive finite number")
        if args.output and args.output.resolve() in {
            args.audio.resolve(), args.transcript.resolve() if args.transcript else None,
        }:
            raise ValueError("--output must differ from the audio and transcript inputs")
        if args.engine_python:
            command = [str(args.engine_python.resolve()), "-B", str(Path(__file__).resolve()),
                       str(args.audio.resolve()), "--model", args.model,
                       "--language", args.language, "--align-model", args.align_model,
                       "--cache-dir", str(args.cache_dir.resolve()), "--device", args.device,
                       "--compute-type", args.compute_type, "--batch-size", str(args.batch_size)]
            for option, value in [("--transcript", args.transcript), ("--output", args.output)]:
                if value is not None:
                    command.extend([option, str(value.resolve())])
            return _run_engine(command, args.timeout)
        transcript = None
        if args.transcript:
            transcript = args.transcript.read_text(encoding="utf-8-sig")
            if args.transcript.suffix.lower() == ".json":
                transcript = json.loads(transcript)
                if isinstance(transcript, dict):
                    transcript = transcript.get("segments")
                if transcript is None:
                    raise ValueError("JSON transcript requires a segment array or {segments: [...]}")
        words = align(args.audio, model=args.model, language=args.language,
                      align_model=args.align_model, transcript=transcript,
                      cache_dir=args.cache_dir, device=args.device,
                      compute_type=args.compute_type, batch_size=args.batch_size)
        output = json.dumps(words, ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        print(output)
        return 0
    except (EngineUnavailable, FileNotFoundError) as exc:
        status, code = "unavailable", 3
        error = str(exc)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        status, code = "error", 2
        error = str(exc)
    except KeyboardInterrupt:
        status, code, error = "cancelled", 130, "Alignment cancelled"
    print(json.dumps({"status": status, "engine": "whisperx", "error": error,
                      "hint": "Run --setup-command for a separate environment; use --python "
                      "to select it. FFmpeg must be on PATH. For Windows DLL errors, check "
                      "the engine's Microsoft Visual C++ runtime and use an environment approved by "
                      "machine application policy. Check model access and transcript bounds."},
                     ensure_ascii=False))
    return code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
