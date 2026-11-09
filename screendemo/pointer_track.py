"""Export scripted pointer actions without moving the OS cursor or starting capture.

Input: JSON array of {timestamp, x, y, click?}. Timestamps and recording_start
MUST use the same clock and unit (seconds by default). Output timestamps are
seconds since recording start, never since the first action. No wall/monotonic
clock conversion is guessed. Click means an action, not a held button state.

CaptureGeometry describes the recorded rectangle in physical desktop pixels.
For ``viewport`` input, x/y are CSS client coordinates; viewport_left/top is the
physical desktop location of the page's client origin, including browser chrome.
Use devicePixelRatio as dpi_scale (including page zoom), measured for that take.
``screen`` is physical desktop coordinates, ``capture`` is physical pixels from
the recorded rectangle's top left, and ``normalized`` is already fractions.
Mixed-DPI monitors require geometry for the monitor/window actually recorded;
one scalar cannot describe a capture spanning different DPI scales.

Example (record a 1500x900 window at desktop (200,100), client origin (215,220)):
  python screendemo/pointer_track.py actions.json --recording-start 1000 \
    --time-unit milliseconds --width 1500 --height 900 --left 200 --top 100 \
    --viewport-left 215 --viewport-top 220 --dpi-scale 1.5 --output track.json

``--format openscreen --openscreen-start-ms <recordingStartedAt>`` exports
{events: [{at, x, y, click}]} for OpenScreen's setPointerTrack arguments. ``at``
is epoch milliseconds; supply the actual take's recordingStartedAt explicitly,
even if the input clock is monotonic. Add projectId when calling that tool.
This is a payload export only: it neither invokes OpenScreen nor writes its
.cursor.json sidecar. Cap/OpenScreen are optional and are never imported.

Library: normalize_events(...), to_openscreen_events(track, start_ms).
CLI stdout: one JSON result, exit 0 success / 2 invalid input or I/O error.
Output files are created exclusively; existing files are never overwritten.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
import sys


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


@dataclass(frozen=True)
class CaptureGeometry:
    """Recorded bounds and CSS client origin, all origins in desktop pixels."""

    width: float
    height: float
    left: float = 0.0
    top: float = 0.0
    dpi_scale: float = 1.0
    viewport_left: float | None = None
    viewport_top: float | None = None

    def __post_init__(self) -> None:
        for name in ("width", "height", "left", "top", "dpi_scale"):
            value = _number(getattr(self, name), name)
            if name in ("width", "height", "dpi_scale") and value <= 0:
                raise ValueError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        for name, default in (("viewport_left", self.left), ("viewport_top", self.top)):
            value = getattr(self, name)
            object.__setattr__(self, name, default if value is None else _number(value, name))

    def normalize(self, x: float, y: float, space: str = "viewport") -> tuple[float, float]:
        """Map a point to capture fractions; do not clamp or hide bad geometry."""
        x, y = _number(x, "x"), _number(y, "y")
        if space == "viewport":
            x = (self.viewport_left - self.left + x * self.dpi_scale) / self.width
            y = (self.viewport_top - self.top + y * self.dpi_scale) / self.height
        elif space == "screen":
            x, y = (x - self.left) / self.width, (y - self.top) / self.height
        elif space == "capture":
            x, y = x / self.width, y / self.height
        elif space != "normalized":
            raise ValueError(f"Unknown coordinate space: {space}")
        return _number(x, "normalized x"), _number(y, "normalized y")


def normalize_events(
    events: Iterable[Mapping],
    *,
    recording_start: float,
    geometry: CaptureGeometry,
    coordinate_space: str = "viewport",
    time_unit: str = "seconds",
    duration: float | None = None,
    outside: str = "error",
) -> dict:
    """Create a v1 track; duration is always seconds, regardless of input unit.

    Pre-start and post-duration events are discarded and counted, so a click
    before capture cannot become a click at zero. Endpoints are inclusive.
    Out-of-bounds positions raise by default; ``drop`` or ``clamp`` is explicit.
    Events are stably sorted by time; equal-time clicks are kept. No input edits,
    interpolation or synthetic clicks. Empty tracks are valid.
    """
    if coordinate_space not in ("viewport", "screen", "capture", "normalized"):
        raise ValueError(f"Unknown coordinate space: {coordinate_space}")
    if time_unit not in ("seconds", "milliseconds"):
        raise ValueError("time_unit must be seconds or milliseconds")
    if outside not in ("error", "drop", "clamp"):
        raise ValueError("outside must be error, drop or clamp")
    start = _number(recording_start, "recording_start")
    if duration is not None:
        duration = _number(duration, "duration")
        if duration < 0:
            raise ValueError("duration must be nonnegative")
    divisor = 1000.0 if time_unit == "milliseconds" else 1.0
    normalized = []
    dropped_time = dropped_position = clamped_position = 0
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise ValueError(f"event {index} must be an object")
        if not all(name in event for name in ("timestamp", "x", "y")):
            raise ValueError(f"event {index} requires timestamp, x and y")
        timestamp = _number(
            (_number(event["timestamp"], f"event {index} timestamp") - start) / divisor,
            f"event {index} offset",
        )
        x, y = geometry.normalize(event["x"], event["y"], coordinate_space)
        click = event.get("click", False)
        if not isinstance(click, bool):
            raise ValueError(f"event {index} click must be a boolean")
        if timestamp < 0 or (duration is not None and timestamp > duration):
            dropped_time += 1
            continue
        if not (0 <= x <= 1 and 0 <= y <= 1):
            if outside == "error":
                raise ValueError(f"event {index} is outside capture bounds: ({x}, {y})")
            if outside == "drop":
                dropped_position += 1
                continue
            x, y = min(1.0, max(0.0, x)), min(1.0, max(0.0, y))
            clamped_position += 1
        normalized.append({"timestamp": timestamp, "x": x, "y": y, "click": click})
    normalized.sort(key=lambda event: event["timestamp"])
    return {
        "schema_version": 1,
        "time_origin": "recording_start",
        "timestamp_unit": "seconds",
        "coordinate_space": "normalized",
        "events": normalized,
        "diagnostics": {
            "dropped_time": dropped_time,
            "dropped_position": dropped_position,
            "clamped_position": clamped_position,
        },
    }


def to_openscreen_events(track: Mapping, recording_started_at_ms: float) -> list[dict]:
    """Return setPointerTrack events on the take's explicit epoch-ms clock.

    Validates the canonical contract even when track was read from external JSON.
    It does not test for, install or invoke an OpenScreen executable.
    """
    start = _number(recording_started_at_ms, "recording_started_at_ms")
    if start < 0:
        raise ValueError("recording_started_at_ms must be nonnegative epoch milliseconds")
    if not isinstance(track, Mapping) or any(
        track.get(key) != value for key, value in (
            ("schema_version", 1), ("time_origin", "recording_start"),
            ("timestamp_unit", "seconds"), ("coordinate_space", "normalized"),
        )
    ):
        raise ValueError("Expected a normalized v1 pointer track with recording-start seconds")
    events = track.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("OpenScreen setPointerTrack requires at least one event")
    checked = normalize_events(
        events, recording_start=0, geometry=CaptureGeometry(1, 1),
        coordinate_space="normalized",
    )
    if checked["diagnostics"]["dropped_time"]:
        raise ValueError("track timestamps must be nonnegative")
    return [
        {"at": _number(start + event["timestamp"] * 1000, "OpenScreen at"),
         "x": event["x"], "y": event["y"], "click": event["click"]}
        for event in checked["events"]
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="JSON array of timestamp/x/y/click actions")
    parser.add_argument("--recording-start", required=True, type=float)
    parser.add_argument("--time-unit", choices=("seconds", "milliseconds"), default="seconds")
    parser.add_argument("--duration", type=float, help="Recording duration in seconds")
    parser.add_argument("--width", required=True, type=float, help="Capture width in physical pixels")
    parser.add_argument("--height", required=True, type=float, help="Capture height in physical pixels")
    parser.add_argument("--left", type=float, default=0)
    parser.add_argument("--top", type=float, default=0)
    parser.add_argument("--viewport-left", type=float)
    parser.add_argument("--viewport-top", type=float)
    parser.add_argument("--dpi-scale", type=float, default=1)
    parser.add_argument("--coordinate-space", choices=("viewport", "screen", "capture", "normalized"), default="viewport")
    parser.add_argument("--outside", choices=("error", "drop", "clamp"), default="error")
    parser.add_argument("--format", choices=("normalized", "openscreen"), default="normalized")
    parser.add_argument("--openscreen-start-ms", type=float, help="Take's epoch-ms recordingStartedAt")
    parser.add_argument("--output", type=Path, help="Fresh output path; parent directory must exist")
    args = parser.parse_args(argv)
    try:
        if args.format == "openscreen" and args.openscreen_start_ms is None:
            raise ValueError("OpenScreen export requires --openscreen-start-ms from the recorded take")
        if args.format != "openscreen" and args.openscreen_start_ms is not None:
            raise ValueError("--openscreen-start-ms requires --format openscreen")
        events = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(events, list):
            raise ValueError("Input must be a JSON array of pointer actions")
        geometry = CaptureGeometry(
            width=args.width, height=args.height, left=args.left, top=args.top,
            dpi_scale=args.dpi_scale, viewport_left=args.viewport_left, viewport_top=args.viewport_top,
        )
        track = normalize_events(
            events, recording_start=args.recording_start, geometry=geometry,
            coordinate_space=args.coordinate_space, time_unit=args.time_unit,
            duration=args.duration, outside=args.outside,
        )
        payload = {"events": to_openscreen_events(track, args.openscreen_start_ms)} if args.format == "openscreen" else track
        serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        result = {"status": "ok", "format": args.format, "event_count": len(track["events"]),
                  "diagnostics": track["diagnostics"]}
        if args.output:
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
            result["output"] = str(args.output.resolve())
        else:
            result["track"] = payload
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
