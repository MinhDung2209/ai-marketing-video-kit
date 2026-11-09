"""Optional HyperFrames 0.9.26 picture renderer; tools/render.py stays independent.

Install explicitly outside the kit, for example (PowerShell):
  npm.cmd install --prefix D:/hf-engine --cache D:/hf-cache/npm --ignore-scripts hyperframes@0.9.26
Then use the kit Python:
  python tools/render_hyperframes.py PROJECT --out D:/renders/picture.mp4 \
    --cli D:/hf-engine/node_modules/hyperframes/bin/hyperframes.mjs \
    --browser D:/path/to/chrome.exe --cache-dir D:/hf-cache --config-dir D:/hf-config

Never installs/downloads an engine or browser. Dependencies are checked lazily.
Stdout is one JSON object, including failures (exit 3 unavailable, 2 error,
124 timeout, 130 cancelled). HTML/assets are copied before invoking the CLI.
Staged audio is excluded with data-hidden; video is muted. Both upstream and
final files are probed for zero audio streams. FFmpeg copies ONLY the video
stream. Mix the kit's audio separately after this step. Dynamically inserted
audio that escapes staging fails verification rather than enabling mixing.

The published 0.9.26 pin does NOT certify post-release fix c38ac5438. Motion
blur parity needs a separate exact-source build or verified later release;
this adapter intentionally rejects other reported CLI versions.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import html
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time


VERSION = "0.9.26"
MOTION_BLUR_FIX = "c38ac5438c751094a720c55c68bd15fc6450ec37"


class RenderError(Exception):
    def __init__(self, message: str, status: str = "error"):
        super().__init__(message)
        self.status = status


class _WindowsJob:
    """Kill only this command's descendants, even if its parent exits first."""

    def __init__(self, process: subprocess.Popen):
        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t),
                        ("max_ws", ctypes.c_size_t), ("active", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("scheduling", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in
                        ("read_ops", "write_ops", "other_ops", "read", "write", "other")]

        class Limits(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]

        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                     ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise RenderError("Cannot create Windows process cleanup job")
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            self.close()
            raise RenderError("Cannot attach renderer to Windows process cleanup job")

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _run(command, *, cwd, env, deadline, log):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RenderError("Render time budget exhausted", "timeout")
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} \
        if os.name == "nt" else {"start_new_session": True}
    with log.open("wb") as stream:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, **kwargs)
        job = None
        try:
            if os.name == "nt":
                job = _WindowsJob(process)
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise RenderError(f"Command timed out: {Path(command[0]).name}", "timeout") from exc
        finally:
            if job:
                job.close()
            elif os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10,
                               creationflags=subprocess.CREATE_NO_WINDOW)
            process.wait(timeout=10)
    # CLI chatter stays out of JSON stdout. Bound diagnostics even on noisy failures.
    with log.open("rb") as stream:
        stream.seek(max(0, log.stat().st_size - 6000))
        tail = stream.read().decode("utf-8", errors="replace")
    if process.returncode:
        raise RenderError(f"Command exited {process.returncode}: {tail.strip()}")
    return tail


class _MuteHTML(HTMLParser):
    """Change media start tags only, preserving script/CSS/text bytes and IDs."""

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for match in re.finditer("\n", source):
            self.offsets.append(match.end())
        self.edits = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"audio", "video"}:
            return
        raw = self.get_starttag_text()
        line, col = self.getpos()
        start = self.offsets[line - 1] + col
        removed = {"muted", "data-has-audio", "data-volume", "autoplay"}
        if tag == "audio":
            removed.add("data-hidden")
        attrs = [(key, value) for key, value in attrs if key not in removed]
        rendered = "".join(" " + key + ("" if value is None else
                           '="' + html.escape(value, quote=True) + '"') for key, value in attrs)
        hidden = ' data-hidden="true"' if tag == "audio" else ""
        new = f'<{tag}{rendered} muted data-has-audio="false" data-volume="0"{hidden}>'
        self.edits.append((start, start + len(raw), new))

    handle_startendtag = handle_starttag

    def result(self):
        self.feed(self.source)
        output = self.source
        for start, end, replacement in reversed(self.edits):
            output = output[:start] + replacement + output[end:]
        return output, len(self.edits)


def _executable(value, label):
    found = shutil.which(str(value))
    if not found or Path(found).suffix.lower() in {".cmd", ".bat", ".ps1"}:
        raise RenderError(f"{label} unavailable: {value}. Supply an installed executable; "
                          "for the CLI use --cli /path/to/hyperframes.mjs with --node.",
                          "unavailable")
    return str(Path(found).resolve())


def _cli_command(value, node):
    path = Path(value)
    if path.suffix.lower() in {".js", ".mjs", ".cjs"}:
        if not path.is_file():
            raise RenderError(f"HyperFrames unavailable: {value}. Install hyperframes@{VERSION} "
                              "in a caller-owned directory and pass --cli.", "unavailable")
        return [_executable(node, "Node.js"), str(path.resolve())]
    return [_executable(value, "HyperFrames")]


def _inside(path, parent):
    return path == parent or parent in path.parents


def render(args):
    started = time.monotonic()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise RenderError("--timeout must be finite and positive")
    deadline = started + args.timeout
    project = Path(args.project).resolve()
    output = Path(args.out).resolve()
    cache = Path(args.cache_dir).resolve()
    config = Path(args.config_dir).resolve()
    if not project.is_dir() or not (project / "index.html").is_file():
        raise RenderError("Project must be a directory containing index.html")
    for name, path in (("output", output), ("cache", cache), ("config", config)):
        if _inside(path, project):
            raise RenderError(f"{name} must be outside the source project to prevent mutation")
    if output.suffix.lower() != ".mp4":
        raise RenderError("--out must be an .mp4 picture file")
    if output.exists() and not args.overwrite:
        raise RenderError("Output exists; use --overwrite to replace it after successful rendering")
    if args.fps not in {24, 25, 30, 60} or not 1 <= args.workers <= 16:
        raise RenderError("Use fps 24/25/30/60 and workers 1..16")
    if not math.isfinite(args.start) or args.start < 0 or (args.end is not None and
            (not math.isfinite(args.end) or args.end <= args.start)):
        raise RenderError("Require finite 0 <= --start < --end")
    command = _cli_command(args.cli, args.node)
    ffmpeg = _executable(args.ffmpeg, "FFmpeg")
    ffprobe = _executable(args.ffprobe, "ffprobe")
    browser = _executable(args.browser, "Chrome")
    cache.mkdir(parents=True, exist_ok=True)
    config.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="render-hf-", dir=cache) as work_name:
        work = Path(work_name)
        temp = work / "tmp"
        temp.mkdir()
        env = os.environ.copy()
        env.update({"HYPERFRAMES_CACHE_DIR": str(cache),
                    "HYPERFRAMES_CONFIG_DIR": str(config),
                    "HYPERFRAMES_EXTRACT_CACHE_DIR": str(cache / "frames"),
                    "HYPERFRAMES_FONT_CACHE_DIR": str(cache / "fonts"),
                    "HYPERFRAMES_BROWSER_PATH": browser,
                    "PRODUCER_HEADLESS_SHELL_PATH": browser,
                    "HYPERFRAMES_FFMPEG_PATH": ffmpeg,
                    "HYPERFRAMES_FFPROBE_PATH": ffprobe,
                    "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1",
                    "HYPERFRAMES_NO_ORPHAN_CLEANUP": "1", "CI": "1", "NO_COLOR": "1",
                    "PUPPETEER_CACHE_DIR": str(cache / "chrome"),
                    "XDG_CACHE_HOME": str(cache), "XDG_CONFIG_HOME": str(config),
                    "TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp)})
        version = _run(command + ["--version"], cwd=work, env=env, deadline=deadline,
                       log=work / "version.log")
        if not re.fullmatch(r"v?" + re.escape(VERSION), version.strip()):
            raise RenderError(f"Pinned HyperFrames {VERSION} required; reported {version.strip()!r}",
                              "unavailable")
        staged = work / "project"

        def copy_file(src, dst):
            if time.monotonic() >= deadline:
                raise RenderError("Time budget exhausted copying project", "timeout")
            return shutil.copyfile(src, dst)

        # Never follow links/junctions into an owner's source or outside asset tree.
        for root, dirs, files in os.walk(project, followlinks=False):
            dirs[:] = [name for name in dirs if name != ".git"]
            for name in dirs + files:
                path = Path(root) / name
                if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                    raise RenderError(f"Linked project paths are unsupported; copy assets first: {path}")
        shutil.copytree(project, staged, ignore=shutil.ignore_patterns(".git"), copy_function=copy_file)
        muted = 0
        for path in staged.rglob("*"):
            if path.suffix.lower() in {".html", ".htm"}:
                source = path.read_bytes().decode("utf-8")
                transformed, count = _MuteHTML(source).result()
                if count:
                    path.write_bytes(transformed.encode("utf-8"))
                    muted += count
        raw = work / "render.mp4"
        cmd = command + ["render", str(staged), "--output", str(raw), "--format", "mp4",
                         "--fps", str(args.fps), "--workers", str(args.workers),
                         "--frames-cache-dir", str(cache / "frames"), "--no-browser-gpu",
                         "--no-best-effort", "--no-wait", "--sdr", "--quiet"]
        if args.start or args.end is not None:
            cmd += ["--start", str(args.start)]
        if args.end is not None:
            cmd += ["--end", str(args.end)]
        _run(cmd, cwd=staged, env=env, deadline=deadline, log=work / "render.log")
        raw_probe = json.loads(_run([ffprobe, "-v", "error", "-show_entries",
                                     "stream=codec_type", "-of", "json", str(raw)],
                                    cwd=work, env=env, deadline=deadline, log=work / "raw-probe.log"))
        if any(stream.get("codec_type") == "audio" for stream in raw_probe.get("streams", [])):
            raise RenderError("HyperFrames emitted audio despite staged muting. "
                              "Remove dynamic audio from a separate picture scene; "
                              "upstream audio mixing is not supported by this adapter.")
        picture = work / "picture.mp4"
        _run([ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(raw), "-map", "0:v:0",
              "-c:v", "copy", "-an", "-sn", "-dn", "-movflags", "+faststart", str(picture)],
             cwd=work, env=env, deadline=deadline, log=work / "ffmpeg.log")
        probe = json.loads(_run([ffprobe, "-v", "error", "-show_entries",
                                 "stream=codec_type,codec_name,width,height,nb_frames,duration",
                                 "-of", "json", str(picture)], cwd=work, env=env,
                                deadline=deadline, log=work / "probe.log"))
        streams = probe.get("streams", [])
        if len(streams) != 1 or streams[0].get("codec_type") != "video":
            raise RenderError("Picture-only verification failed: expected exactly one video stream")
        with picture.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        # Publish only a verified file; failed renders leave previous output untouched.
        fd, pending_name = tempfile.mkstemp(prefix=".render-hf-", suffix=".mp4", dir=output.parent)
        os.close(fd)
        pending = Path(pending_name)
        try:
            shutil.copyfile(picture, pending)
            if output.exists() and not args.overwrite:
                raise RenderError("Output appeared during render; refusing replacement")
            os.replace(pending, output)
        finally:
            pending.unlink(missing_ok=True)
        result = {"status": "ok", "engine": "hyperframes", "version": VERSION,
                  "picture_only": True, "audio_streams": 0, "upstream_audio_streams": 0,
                  "muted_media": muted,
                  "artifact": {"path": str(output), "sha256": digest,
                               "size_bytes": output.stat().st_size},
                  "video": {key: streams[0].get(key) for key in
                            ("codec_name", "width", "height", "nb_frames", "duration")},
                  "elapsed_seconds": round(time.monotonic() - started, 3),
                  "motion_blur_parity": "unverified; post-release fix " + MOTION_BLUR_FIX}
    return result


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise RenderError(message)


def main(argv=None):
    try:
        parser = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("project")
        parser.add_argument("--out", required=True)
        parser.add_argument("--cache-dir", required=True)
        parser.add_argument("--config-dir", required=True)
        parser.add_argument("--cli", default="hyperframes")
        parser.add_argument("--node", default="node")
        parser.add_argument("--browser", default=os.environ.get("VIDEOKIT_CHROME", "chrome"))
        parser.add_argument("--ffmpeg", default="ffmpeg")
        parser.add_argument("--ffprobe", default="ffprobe")
        parser.add_argument("--fps", type=int, default=30)
        parser.add_argument("--workers", type=int, default=1)
        parser.add_argument("--start", type=float, default=0)
        parser.add_argument("--end", type=float)
        parser.add_argument("--timeout", type=float, default=600)
        parser.add_argument("--overwrite", action="store_true")
        result = render(parser.parse_args(argv))
        code = 0
    except KeyboardInterrupt:
        result, code = {"status": "cancelled", "error": "Render cancelled; owned processes stopped"}, 130
    except RenderError as exc:
        result = {"status": exc.status, "error": str(exc)}
        code = {"unavailable": 3, "timeout": 124}.get(exc.status, 2)
    except (OSError, ValueError, shutil.Error, subprocess.SubprocessError) as exc:
        result, code = {"status": "error", "error": str(exc)}, 2
    result.setdefault("engine", "hyperframes")
    result.setdefault("version", VERSION)
    print(json.dumps(result, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
