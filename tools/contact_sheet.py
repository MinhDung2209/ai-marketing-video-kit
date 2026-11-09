#!/usr/bin/env python3
"""Build a contact sheet from distinct, real video frames using FFmpeg.

    python tools/contact_sheet.py "short clip.mkv" "contact sheet.png" 8 --json

Frame-index midpoint sampling is adapted from video-shotcraft/shot-polish/sheet.py
(Apache-2.0), commit 1266a3ec4831289c4d893d42dd5102723658039a.
FFmpeg and ffprobe are optional runtime executables; no Python packages or models
are needed. The importable create_contact_sheet() returns ok/error/unavailable.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess


def sample_frame_indices(frame_count: int, requested: int = 8) -> list[int]:
    """Return sorted, distinct midpoint indices within the decoded frame count.

    Unlike duration-based seeking, this also handles single-frame and VFR clips.
    A held picture may repeat visually; its source frame indices remain distinct.
    """
    if frame_count <= 0 or requested <= 0:
        raise ValueError("frame_count and requested must be positive")
    count = min(frame_count, requested)
    return [(2 * k + 1) * frame_count // (2 * count) for k in range(count)]


def _run(command: list[str], timeout: float) -> str:
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, check=False,
    )
    if result.returncode:
        detail = result.stderr.strip()[-2000:] or "no diagnostic output"
        raise ValueError(f"{Path(command[0]).name} exited {result.returncode}: {detail}")
    return result.stdout


def create_contact_sheet(
    source: str | Path,
    output: str | Path,
    requested: int = 8,
    *,
    tile_width: int = 480,
    max_columns: int = 4,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    timeout: float = 120,
    overwrite: bool = False,
) -> dict:
    """Count decoded frames, select unique indices and render one still image.

    The grid uses the largest divisor of the sample count up to max_columns,
    so every cell contains a selected frame (five samples use a 1x5 grid).
    Paths are passed as subprocess arguments, never through a shell. Existing
    output needs overwrite=True; the source can never be used as the output.
    The timeout applies separately to probing and rendering; subprocess.run
    kills and waits for its child when a timeout expires.
    """
    context = {"source": str(source), "output": str(output), "requested": requested}
    try:
        if requested <= 0 or tile_width <= 0 or max_columns <= 0:
            raise ValueError("requested, tile_width and max_columns must be positive")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        src, dst = Path(source).resolve(), Path(output).resolve()
        context.update(source=str(src), output=str(dst))
        if not src.is_file():
            raise ValueError(f"Source file does not exist: {src}")
        if src == dst or (dst.exists() and src.samefile(dst)):
            raise ValueError("Output must differ from the source file")
        if dst.exists() and not overwrite:
            raise ValueError(f"Output already exists; use --overwrite: {dst}")
        if not dst.parent.is_dir():
            raise ValueError(f"Output directory does not exist: {dst.parent}")
        engines = {"ffmpeg": shutil.which(ffmpeg), "ffprobe": shutil.which(ffprobe)}
        missing = [name for name, executable in engines.items() if not executable]
        if missing:
            return {
                **context, "status": "unavailable", "missing": missing,
                "message": "Unavailable: " + ", ".join(missing)
                + "; install FFmpeg on D:/ and set PATH or --ffmpeg/--ffprobe.",
            }
        probe = json.loads(_run([
            engines["ffprobe"], "-v", "error", "-count_frames",
            "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
            "-of", "json", str(src),
        ], timeout))
        streams = probe.get("streams", [])
        if not streams:
            raise ValueError("Source has no video stream")
        try:
            total = int(streams[0]["nb_read_frames"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("ffprobe could not count decoded video frames") from exc
        indices = sample_frame_indices(total, requested)
        columns = min(max_columns, len(indices))
        while len(indices) % columns:
            columns -= 1
        rows = len(indices) // columns
        selection = "+".join(f"eq(n\\,{index})" for index in indices)
        filters = (
            f"select='{selection}',scale={tile_width}:-1,"
            f"tile={columns}x{rows}:nb_frames={len(indices)}"
        )
        _run([
            engines["ffmpeg"], "-v", "error", "-nostdin",
            "-y" if overwrite else "-n", "-i", str(src),
            "-map", "0:v:0", "-an", "-sn", "-dn",
            "-vf", filters, "-frames:v", "1", str(dst),
        ], timeout)
        if not dst.is_file() or dst.stat().st_size == 0:
            raise ValueError("FFmpeg produced no contact-sheet image")
        return {
            **context, "status": "ok", "frame_count": total,
            "sample_count": len(indices), "frame_indices": indices,
            "columns": columns, "rows": rows, "tile_width": tile_width,
        }
    except subprocess.TimeoutExpired:
        return {**context, "status": "error", "message": f"FFmpeg/ffprobe timed out after {timeout}s"}
    except (OSError, ValueError) as exc:
        return {**context, "status": "error", "message": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Source video path")
    parser.add_argument("output", help="Output still image, e.g. .png or .jpg")
    parser.add_argument("requested", nargs="?", type=int, default=8)
    parser.add_argument("--tile-width", type=int, default=480)
    parser.add_argument("--max-columns", type=int, default=4)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print structured status")
    args = parser.parse_args()
    result = create_contact_sheet(
        args.source, args.output, args.requested,
        tile_width=args.tile_width, max_columns=args.max_columns,
        ffmpeg=args.ffmpeg, ffprobe=args.ffprobe, timeout=args.timeout,
        overwrite=args.overwrite,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=True))
    elif result["status"] == "ok":
        print(f'{result["frame_count"]} frames; sheet frames '
              + ",".join(map(str, result["frame_indices"])))
    else:
        print(f'{result["status"]}: {result["message"]}')
    return {"ok": 0, "error": 1, "unavailable": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
