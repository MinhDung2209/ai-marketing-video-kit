"""Optional Windows Cap JSON recorder. Never installs Cap or changes shoot.py.

CLI (stdout is one JSON result; exit 0 ok, 3 unavailable/unsupported, 2 error,
124 timeout, 130 cancelled):
  python screendemo/cap_capture.py --check
  python screendemo/cap_capture.py --screen ID --duration 3 \
    --project D:/captures/take.cap --output D:/captures/take.mp4

Library: ``with CapCapture(project, output, screen="ID") as session: ...``.
The context starts capture, checks status, stops, exports and probes on success;
exceptions always stop and reap owned processes. ``session.result`` is populated
after a successful context exit. ``capture(..., cancel=threading.Event())`` is
the bounded-duration equivalent returning a JSON-compatible result.

Requires an installed native Cap CLI implementing the researched JSON lifecycle
(Cap source a42f8f44f61c02b50302d755c41a7b739947a3e7) and ffprobe. Windows
process containment is mandatory: every command starts suspended, joins a private
kill-on-close Job Object, then resumes. Detached workers inherit that job, even
if start fails before returning their recording ID/PID. Closing the Python
process also closes the job. No global process-name kills are used.

Caller project/output paths must be fresh. The .cap project remains for diagnosis
on failure. A verified MP4 is published without replacing existing files. Cap's
enabled Desktop automation rules are refused because they can upload/delete/run
commands on capture completion. No desktop settings or credentials are changed.
Native Windows capture is unverified until an installed-binary pilot succeeds;
an unavailable result must never be presented as a successful recording.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid


class CapError(RuntimeError):
    def __init__(self, message, status="error"):
        super().__init__(message)
        self.status = status


def _positive(value, name):
    if isinstance(value, bool) or not math.isfinite(float(value)) or float(value) <= 0:
        raise CapError(f"{name} must be positive and finite")
    return float(value)


def _executable(command):
    parts = [os.fspath(command)] if isinstance(command, (str, os.PathLike)) else list(command)
    if not parts or not all(isinstance(p, str) and p for p in parts):
        raise CapError("Expected an executable or a nonempty command argument list")
    resolved = shutil.which(parts[0])
    if not resolved:
        raise CapError(f"Executable unavailable: {parts[0]}. Supply an installed executable path; "
                       "this adapter never installs dependencies.", "unavailable")
    return [resolved, *parts[1:]]


class _WindowsJob:
    """Own a whole process tree, including detached descendants of exited parents."""

    def __init__(self):
        if os.name != "nt":
            raise CapError("Native capture adapter currently supports Windows only", "unsupported")

        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t),
                        ("max_ws", ctypes.c_size_t), ("active", wintypes.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                        ("scheduling", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in
                        ("read_ops", "write_ops", "other_ops", "read", "write", "other")]

        class Limits(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]

        class Accounting(ctypes.Structure):
            _fields_ = [(n, ctypes.c_int64) for n in ("user", "kernel", "period_user", "period_kernel")]
            _fields_ += [(n, wintypes.DWORD) for n in ("faults", "total", "active", "terminated")]

        self.accounting = Accounting
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        for name, args, result in (
            ("CreateJobObjectW", [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            ("SetInformationJobObject", [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            ("AssignProcessToJobObject", [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            ("TerminateJobObject", [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            ("QueryInformationJobObject", [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                            wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            ("OpenProcess", [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            ("WaitForSingleObject", [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            ("CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
        ):
            fn = getattr(self.api, name)
            fn.argtypes, fn.restype = args, result
        self.native = ctypes.WinDLL("ntdll")
        self.native.NtResumeProcess.argtypes = [wintypes.HANDLE]
        self.native.NtResumeProcess.restype = ctypes.c_long
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.api.SetInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            if self.handle:
                self.api.CloseHandle(self.handle)
            self.handle = None
            raise CapError("Windows process containment unavailable", "unsupported")

    def launch(self, args, cwd):
        if not self.handle:
            raise CapError("Owned Cap process job is already closed")
        process = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW | 0x4)  # CREATE_SUSPENDED
        try:
            handle = int(process._handle)
            if not self.api.AssignProcessToJobObject(self.handle, handle):
                raise CapError("Cannot contain Cap process; capture was not started", "unsupported")
            if self.native.NtResumeProcess(handle) != 0:
                raise CapError("Cannot resume contained Cap process", "unsupported")
            return process
        except BaseException:
            process.kill()
            process.communicate()
            raise

    def close(self):
        if not self.handle:
            return
        processes = []
        try:
            # ActiveProcesses reaches zero before Windows finishes signalling
            # every process handle. Pin handles before terminating the tree and
            # wait for teardown as well, so the caller observes no live worker.
            capacity = 64
            while True:
                class ProcessIds(ctypes.Structure):
                    _fields_ = [("assigned", wintypes.DWORD), ("count", wintypes.DWORD),
                                ("ids", ctypes.c_size_t * capacity)]

                ids = ProcessIds()
                if self.api.QueryInformationJobObject(
                        self.handle, 3, ctypes.byref(ids), ctypes.sizeof(ids), None):
                    for pid in ids.ids[:ids.count]:
                        process = self.api.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
                        if process:
                            processes.append(process)
                    break
                if ctypes.get_last_error() != 234 or capacity >= 65536:  # ERROR_MORE_DATA
                    raise CapError("Cannot enumerate owned Cap processes for cleanup")
                capacity *= 2
            if not self.api.TerminateJobObject(self.handle, 1):
                raise CapError("Cannot terminate owned Cap process job")
            deadline = time.monotonic() + 5
            for process in processes:
                remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
                if self.api.WaitForSingleObject(process, remaining_ms) != 0:
                    raise CapError("Owned Cap process did not finish terminating")
            while True:
                info = self.accounting()
                if not self.api.QueryInformationJobObject(
                        self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
                    raise CapError("Cannot verify owned Cap process cleanup")
                if info.active == 0:
                    return
                if time.monotonic() >= deadline:
                    raise CapError(f"Cap cleanup incomplete: {info.active} owned processes remain")
                time.sleep(0.02)
        finally:
            for process in processes:
                self.api.CloseHandle(process)
            self.api.CloseHandle(self.handle)
            self.handle = None


def _decode(stdout):
    text = stdout.decode("utf-8-sig", errors="strict").strip()
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        try:
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise CapError("Cap returned invalid JSON/NDJSON") from exc


class CapCapture:
    """One fresh, explicitly owned native recording; use as a context manager."""

    def __init__(self, project, output, *, screen=None, window=None, cap="cap",
                 ffprobe="ffprobe", duration=30, command_timeout=30, export_timeout=120,
                 cancel=None, fps=30):
        self.project = Path(project).resolve()
        self.output = Path(output).resolve()
        self.cap, self.ffprobe = cap, ffprobe
        self.screen, self.window = screen, window
        self.duration = _positive(duration, "duration")
        self.command_timeout = _positive(command_timeout, "command_timeout")
        self.export_timeout = _positive(export_timeout, "export_timeout")
        if isinstance(fps, bool) or not isinstance(fps, int) or not 1 <= fps <= 120:
            raise CapError("fps must be an integer from 1 to 120")
        self.fps, self.cancel = fps, cancel
        self.job = None
        self.recording_id = None
        self.pid = None
        self.attempted = self.stopped = self.closed = False
        self.cleanup_complete = False
        self.result = None
        self.cleanup_errors = []
        self.pending = self.output.with_name(f".{self.output.stem}.{uuid.uuid4().hex}.mp4")

    def _cancelled(self):
        if self.cancel is not None and self.cancel.is_set():
            raise CapError("Capture cancelled", "cancelled")

    def _run(self, args, *, timeout=None, cleanup=False):
        if not cleanup:
            self._cancelled()
        process = self.job.launch(args, self.project.parent)
        deadline = time.monotonic() + (timeout or self.command_timeout)
        try:
            while True:
                if not cleanup:
                    self._cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CapError(f"Command timed out: {Path(args[0]).name}", "timeout")
                try:
                    stdout, stderr = process.communicate(timeout=min(0.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    pass
            events = _decode(stdout)
            errors = [e["error"] for e in events if isinstance(e, dict) and e.get("error")]
            if process.returncode or errors:
                detail = str(errors[-1]) if errors else stderr.decode("utf-8", errors="replace")[-1500:]
                raise CapError(f"Command failed (exit {process.returncode}): {detail}")
            return events
        finally:
            if process.poll() is None:
                process.kill()
            # Detached Cap workers do not inherit its pipes. The job is the
            # final backstop for descendants, including a broken CLI's pipes.
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                # A faulty CLI may leave a descendant holding its stdout pipe.
                # Kill the owned tree before joining Python's pipe reader threads.
                self.job.close()
                process.communicate(timeout=1)

    def _cap(self, *args, **kwargs):
        return self._run([*self.cap, *map(str, args), "--json"], **kwargs)

    def start(self):
        if self.attempted or self.closed:
            raise CapError("A CapCapture instance can start only once")
        try:
            self._cancelled()
            self.cap = _executable(self.cap)
            self.ffprobe = _executable(self.ffprobe)
            if bool(self.screen is not None) == bool(self.window is not None):
                raise CapError("Specify exactly one screen or window ID (see cap targets --json)")
            if self.project.suffix.lower() != ".cap" or self.output.suffix.lower() != ".mp4":
                raise CapError("project must end in .cap and output must end in .mp4")
            if self.project.exists() or self.output.exists() or self.project.is_symlink() or self.output.is_symlink():
                raise CapError("Project/output already exists; choose fresh caller paths")
            if self.project in self.output.parents:
                raise CapError("Output must be outside the .cap project")
            self.job = _WindowsJob()
            self.project.parent.mkdir(parents=True, exist_ok=True)
            self.output.parent.mkdir(parents=True, exist_ok=True)
            doctor = self._cap("doctor")
            if len(doctor) != 1 or not isinstance(doctor[0], dict):
                raise CapError("Unsupported Cap doctor JSON contract", "unsupported")
            if doctor[0].get("captureReady") is not True or doctor[0].get("ok") is not True:
                raise CapError("Installed Cap is not capture-ready; inspect cap doctor --json", "unsupported")
            automations = doctor[0].get("automations", {})
            if automations.get("enabledCount") != 0:
                raise CapError("Cap Desktop automation rules must be disabled for local capture", "unsupported")
            self.attempted = True  # Set BEFORE start: failed/invalid replies may hide a live worker.
            target = ("--screen", self.screen) if self.screen is not None else ("--window", self.window)
            events = self._cap("record", "start", "--detach", *target,
                               "--path", self.project, "--duration", self.duration,
                               "--fps", self.fps)
            started = next((e for e in events if isinstance(e, dict) and e.get("type") == "started"), None)
            if not started or not isinstance(started.get("recordingId"), str) or not started["recordingId"]:
                raise CapError("Cap start did not return a recordingId")
            if Path(started.get("path", "")).resolve() != self.project:
                raise CapError("Cap start returned a different project path")
            self.recording_id, self.pid = started["recordingId"], started.get("pid")
            self.status()
            return started
        except BaseException:
            self.close()
            raise

    def status(self):
        if not self.recording_id or self.closed:
            raise CapError("Recording has not started or is closed")
        events = self._cap("record", "status")
        rows = events[0] if len(events) == 1 and isinstance(events[0], list) else []
        row = next((r for r in rows if isinstance(r, dict) and r.get("recordingId") == self.recording_id), None)
        if row is None or not (row.get("status") == "stopped" or
                               (row.get("status") == "recording" and row.get("alive") is True)):
            raise CapError(f"Owned recording is not alive: {row}")
        return row

    def stop(self, *, cleanup=False):
        if not self.attempted or self.stopped:
            return
        selector = ("--id", self.recording_id) if self.recording_id else ("--path", self.project)
        events = self._cap("record", "stop", *selector, "--timeout", self.command_timeout,
                           timeout=self.command_timeout + 2, cleanup=cleanup)
        stopped = next((e for e in events if isinstance(e, dict) and e.get("type") == "stopped"), None)
        if not stopped or stopped.get("recordingMetaExists") is not True:
            raise CapError("Cap did not finalize recording metadata")
        if Path(stopped.get("path", "")).resolve() != self.project:
            raise CapError("Cap stop returned a different project path")
        self.stopped = True
        return stopped

    def finish(self):
        self.stop()
        events = self._cap("export", self.project, "--output", self.pending,
                           "--format", "mp4", timeout=self.export_timeout)
        if not any(isinstance(e, dict) and e.get("type") == "Completed" for e in events):
            raise CapError("Cap export did not return a Completed event")
        probe = self._run([*self.ffprobe, "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(self.pending)])[0]
        streams = probe.get("streams", [])
        duration = float(probe.get("format", {}).get("duration", 0))
        if not math.isfinite(duration) or duration <= 0 or not any(
                s.get("codec_type") == "video" and s.get("width", 0) > 0 and s.get("height", 0) > 0
                for s in streams):
            raise CapError("ffprobe found no positive-duration video")
        self._cancelled()
        with self.pending.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        os.link(self.pending, self.output)  # Atomic, same-directory, no replacement.
        self.result = {"status": "ok", "engine": "cap", "recording_id": self.recording_id,
                       "project": str(self.project), "duration": duration,
                       "artifacts": [{"path": str(self.output), "sha256": digest,
                                      "size_bytes": self.output.stat().st_size}],
                       "probe": probe}
        return self.result

    def close(self):
        if self.closed:
            return
        try:
            if self.job and self.job.handle:
                try:
                    try:
                        self.stop(cleanup=True)
                    except (CapError, OSError, ValueError) as exc:
                        self.cleanup_errors.append(str(exc))
                finally:
                    self.job.close()
            self.cleanup_complete = True
        finally:
            self.closed = True
            self.pending.unlink(missing_ok=True)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.finish()
        finally:
            self.close()
        return False


def capture(project, output, **kwargs):
    """Record for duration seconds; cancellation/timeout are explicit results."""
    session = None
    try:
        session = CapCapture(project, output, **kwargs)
        with session:
            deadline = time.monotonic() + session.duration
            next_status = time.monotonic() + 1
            while time.monotonic() < deadline:
                session._cancelled()
                if time.monotonic() >= next_status:
                    if session.status()["status"] == "stopped":
                        break
                    next_status = time.monotonic() + 1
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        result = session.result
    except KeyboardInterrupt:
        result = {"status": "cancelled", "engine": "cap", "error": "Capture interrupted", "artifacts": []}
    except (CapError, OSError, ValueError, TypeError) as exc:
        result = {"status": getattr(exc, "status", "error"), "engine": "cap",
                  "error": str(exc), "artifacts": []}
    if session is not None:
        result["cleanup"] = {"complete": session.cleanup_complete, "stop_errors": session.cleanup_errors}
    return result


def check_available(cap="cap"):
    """Read-only executable/platform check; no capture or dependency installation."""
    try:
        command = _executable(cap)
        if os.name != "nt":
            raise CapError("Native capture adapter currently supports Windows only", "unsupported")
        return {"status": "ok", "engine": "cap", "command": command,
                "note": "Executable located; recording still requires capture-ready doctor and a native pilot"}
    except CapError as exc:
        return {"status": exc.status, "engine": "cap", "error": str(exc), "artifacts": []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--cap", default="cap")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--project")
    parser.add_argument("--output")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--screen")
    target.add_argument("--window")
    parser.add_argument("--duration", type=float, default=5)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--command-timeout", type=float, default=30)
    parser.add_argument("--export-timeout", type=float, default=120)
    args = parser.parse_args(argv)
    # SIGTERM is converted to a Python unwind so the same finally cleanup runs.
    def interrupted(*_):
        raise KeyboardInterrupt()

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.check:
            result = check_available(args.cap)
        elif not args.project or not args.output:
            result = {"status": "error", "engine": "cap", "error": "--project and --output are required", "artifacts": []}
        else:
            options = vars(args).copy()
            for key in ("check", "project", "output"):
                options.pop(key)
            result = capture(args.project, args.output, **options)
        print(json.dumps(result, ensure_ascii=False))
        return {"ok": 0, "unavailable": 3, "unsupported": 3, "timeout": 124,
                "cancelled": 130}.get(result["status"], 2)
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(main())
