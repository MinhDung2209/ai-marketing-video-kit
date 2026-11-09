"""Optional, bounded Streamlink HLS capture (not a VOD/metadata downloader).

Example with an already installed Streamlink engine:
  python tools/live_capture.py hls://https://example.org/live.m3u8 \
    --out D:/captures/live.ts --duration 30 --cancel-file D:/captures/stop

Duration is a wall-clock budget INCLUDING engine startup/network waits, plus
bounded process cleanup. OS process creation itself may be uninterruptible.
Streamlink also limits media duration to this budget,
rounded to HLS segments. Output is the original stream bytes, without remuxing;
use .ts for MPEG-TS HLS. Partial bytes at the budget/cancellation are preserved,
but are not guaranteed decodable (e.g. cancellation before the first segment).
Existing outputs are never overwritten. Nothing is installed automatically.

Python API: capture_live(..., cancel_event=threading.Event()). CLI cancellation:
Ctrl+C, SIGTERM, Windows Ctrl+Break, or creation of --cancel-file. Stdout is one
JSON result. Exit codes: 0 ok, 2 error, 3 unavailable, 124 timeout without data,
130 cancelled. No default Streamlink configs, plugin caches or sideloading.
"""

from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit


class _WindowsJob:
    """Own the engine's descendants, including any HLS audio muxer."""

    def __init__(self, process):
        from ctypes import wintypes

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
        self.api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                       ctypes.c_void_p, wintypes.DWORD,
                                                       ctypes.c_void_p]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            self.close()
            raise OSError("Cannot create Windows engine cleanup job")
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            self.close()
            raise OSError("Cannot attach Streamlink to Windows engine cleanup job")

    def close(self):
        if self.handle:
            # Windows venv launchers can exit before the interpreter child has
            # released inherited output handles. Wait for the owned tree, not
            # just Popen's immediate child, before publishing/removing staging.
            class Accounting(ctypes.Structure):
                _fields_ = [(name, ctypes.c_int64) for name in
                            ("user", "kernel", "period_user", "period_kernel")] + [
                                (name, ctypes.c_uint32) for name in
                                ("faults", "total", "active", "terminated")]

            self.api.TerminateJobObject(self.handle, 1)
            deadline = time.monotonic() + 5
            info = Accounting()
            try:
                while self.api.QueryInformationJobObject(
                        self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None) and info.active:
                    if time.monotonic() >= deadline:
                        raise OSError("Timed out waiting for Streamlink process-tree cleanup")
                    time.sleep(0.01)
            finally:
                self.api.CloseHandle(self.handle)
                self.handle = None


def _engine_command(executable):
    if executable is not None:
        found = shutil.which(str(executable))
        if found and Path(found).suffix.lower() not in {".cmd", ".bat", ".ps1"}:
            return [str(Path(found).resolve())]
        return None  # Explicit engine selection never silently falls back.
    if importlib.util.find_spec("streamlink") is not None:
        return [sys.executable, "-m", "streamlink"]
    found = shutil.which("streamlink")
    return [found] if found and Path(found).suffix.lower() not in {".cmd", ".bat", ".ps1"} else None


def _stop(process, job):
    if job is not None:
        job.close()
    elif os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()  # Assignment failed before an owned job was established.
    process.wait(timeout=5)


def capture_live(url, output, *, duration, stream="best", streamlink=None,
                 cancel_event=None, cancel_file=None):
    """Capture HLS with a required finite budget; return a JSON-safe receipt.

    A nonempty partial recording is published for budget/cancel, with partial
    true. Engine errors discard staging bytes. Status ok certifies acquisition,
    not codec/container validity; downstream callers can ffprobe the artifact.
    """
    started = time.monotonic()
    result = {"status": "error", "reason": None, "output": None,
              "bytes": 0, "partial": False, "elapsed_seconds": 0.0,
              "duration_budget_seconds": None, "engine_exit_code": None}
    staging = None

    def cancelled():
        return ((cancel_event is not None and cancel_event.is_set()) or
                (cancel_file is not None and Path(cancel_file).exists()))

    try:
        duration = float(duration)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duration must be finite and greater than zero")
        result["duration_budget_seconds"] = duration
        deadline = started + duration
        if not isinstance(url, str) or not url.strip():
            raise ValueError("A live HTTP(S) or hls:// HTTP(S) URL is required")
        parsed = urlsplit(url[6:] if url.startswith("hls://") else url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("A live HTTP(S) or hls:// HTTP(S) URL is required")
        if not isinstance(stream, str) or not stream or stream.startswith("-"):
            raise ValueError("stream must be a nonempty Streamlink stream name")
        destination = Path(output).expanduser().absolute()
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"Output already exists: {destination}")
        if cancelled():
            result.update(status="cancelled", reason="cancelled")
            return result
        command = _engine_command(streamlink)
        if command is None:
            result.update(status="unavailable", reason="streamlink_unavailable",
                          message="Streamlink unavailable. Install it in an optional D:/ engine "
                                  "environment and pass --streamlink PATH/streamlink.exe, or "
                                  "make its module available to this Python. No engine was installed.")
            return result
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".live-capture-", suffix=".part", dir=destination.parent)
        staging = Path(name)
        # Logs are temporary in the caller's output directory, never system TEMP.
        with os.fdopen(fd, "wb", buffering=0) as media, tempfile.TemporaryFile(
                mode="w+b", dir=destination.parent) as log:
            command += ["--no-config", "--no-plugin-cache", "--no-plugin-sideloading",
                        "--auto-version-check", "no", "--loglevel", "warning", "--stdout",
                        "--stream-types", "hls", "--stream-segmented-duration", str(duration),
                        "--url", url, "--default-stream", stream]
            kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} \
                if os.name == "nt" else {"start_new_session": True}
            process = None
            job = None
            reason = "stream_ended"
            try:
                if cancelled():
                    reason = "cancelled"
                elif time.monotonic() >= deadline:
                    reason = "duration_budget"
                else:
                    process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                               stdout=media, stderr=log, **kwargs)
                    if os.name == "nt":
                        job = _WindowsJob(process)
                    while True:
                        if cancelled():
                            reason = "cancelled"
                            break
                        if process.poll() is not None:
                            break
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            reason = "duration_budget"
                            break
                        time.sleep(min(0.05, remaining))
            except KeyboardInterrupt:
                reason = "cancelled"
            finally:
                if process is not None:
                    _stop(process, job)
                    result["engine_exit_code"] = process.returncode
            if reason == "stream_ended" and process is not None and process.returncode != 0:
                # Keep stdout machine-readable and cap diagnostic size.
                log.seek(0, os.SEEK_END)
                log.seek(max(0, log.tell() - 4000))
                diagnostic = log.read().decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"Streamlink exited {process.returncode}: {diagnostic}")
        size = staging.stat().st_size
        result.update(reason=reason, partial=reason != "stream_ended")
        if reason == "cancelled":
            result["status"] = "cancelled"
        elif not size:
            result.update(status="timeout" if reason == "duration_budget" else "error",
                          message="No stream bytes were captured")
        else:
            result["status"] = "ok"
        if size:
            # Atomic no-clobber publication on NTFS/POSIX, even if another caller
            # created the destination during capture. Staging shares its volume.
            os.link(staging, destination)
            result.update(output=str(destination), bytes=size)
    except KeyboardInterrupt:
        result.update(status="cancelled", reason="cancelled")
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        result.update(status="error", reason="capture_failed", message=str(exc))
    finally:
        if staging is not None:
            # Antivirus/indexing can briefly retain a handle after process exit.
            for attempt in range(20):
                try:
                    staging.unlink(missing_ok=True)
                    break
                except PermissionError:
                    if attempt == 19:
                        result.update(status="error", reason="cleanup_failed",
                                      message=f"Cannot remove staging file: {staging}")
                    else:
                        time.sleep(0.05)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Live page URL, or hls://https://.../live.m3u8")
    parser.add_argument("--out", required=True, help="New output file; raw stream, no remux")
    parser.add_argument("--duration", required=True, type=float, help="Wall-clock budget in seconds")
    parser.add_argument("--stream", default="best", help="Streamlink quality selection (default: best)")
    parser.add_argument("--streamlink", help="Optional installed Streamlink executable")
    parser.add_argument("--cancel-file", help="Stop when this caller-owned marker exists; never deleted")
    args = parser.parse_args(argv)
    event = threading.Event()
    previous = {}
    try:
        for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            if hasattr(signal, name):
                sig = getattr(signal, name)
                previous[sig] = signal.signal(sig, lambda *_: event.set())
        result = capture_live(args.url, args.out, duration=args.duration, stream=args.stream,
                              streamlink=args.streamlink, cancel_event=event, cancel_file=args.cancel_file)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    return {"ok": 0, "unavailable": 3, "timeout": 124, "cancelled": 130}.get(result["status"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
