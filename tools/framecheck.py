#!/usr/bin/env python3
"""Check seek determinism, rendered frame parity and single-frame transients.

    python tools/framecheck.py PROJECT --render out.mp4 --times 0,0.5,1
    python tools/framecheck.py --render clip.mp4 --flicker-only --output receipt.json

Import check_frames() for a JSON-compatible result. stdout is JSON; exit codes:
0 passed, 1 measured defect, 2 invalid input/runtime error, 3 unavailable engine.
No files are written unless --output is supplied; the source project is read only.
FFmpeg/ffprobe, Pillow and (only for HTML snapshots) Playwright/Chromium are
optional. Nothing is installed or downloaded. No NumPy dependency is needed.

Metric concepts: ghost-editor/scripts/framecheck.py, MIT, research commit
ce172726c36293722b08eb57b5b307d4f06389e8. This implementation uses the kit's
existing render.SEEK_JS contract instead of requiring the HyperFrames CLI.
Parity assumes a constant-frame-rate render starting at timeline time zero.
Thresholds are configurable heuristics, not human watch/listen approval.
"""

from __future__ import annotations

import argparse
from collections import deque
from fractions import Fraction
import importlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import threading


class Unavailable(RuntimeError):
    """An optional engine is missing or cannot be launched."""


def _pillow():
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError as exc:
        raise Unavailable("Pillow unavailable; install Pillow in the D:/ kit venv") from exc
    return Image, ImageChops, ImageStat


def _run(command, timeout):
    process = subprocess.run(command, capture_output=True, timeout=timeout,
                             stdin=subprocess.DEVNULL, check=False)
    if process.returncode:
        detail = process.stderr.decode("utf-8", "replace")[-2000:]
        raise ValueError(f"{Path(command[0]).name} exited {process.returncode}: {detail}")
    return process.stdout


def _probe(video, executable, timeout):
    data = json.loads(_run([
        executable, "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=width,height,avg_frame_rate,r_frame_rate,nb_read_frames",
        "-of", "json", str(video),
    ], timeout))
    if not data.get("streams"):
        raise ValueError("Render contains no video stream")
    stream = data["streams"][0]
    fps = float(Fraction(stream["avg_frame_rate"]))
    count = int(stream["nb_read_frames"])
    width, height = int(stream["width"]), int(stream["height"])
    if not math.isfinite(fps) or fps <= 0 or count <= 0 or min(width, height) <= 0:
        raise ValueError("Render must contain decodable frames and a positive frame rate")
    return {"width": width, "height": height, "fps": fps, "frames": count,
            "nominal_fps": float(Fraction(stream["r_frame_rate"]))}


def image_metrics(a, b):
    """RGB pixel errors; PSNR=99 for identical images to keep JSON finite."""
    _, ImageChops, ImageStat = _pillow()
    if a.size != b.size:
        raise ValueError(f"Frame dimensions differ: snapshot {a.size}, render {b.size}")
    difference = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    stats = ImageStat.Stat(difference)
    mse = sum(value * value for value in stats.rms) / 3
    histogram = difference.histogram()
    changed = sum(sum(histogram[channel * 256 + 9:(channel + 1) * 256])
                  for channel in range(3))
    return {"mean_abs_diff": round(sum(stats.mean) / 3, 6),
            "max_abs_diff": max(high for _, high in stats.extrema),
            "changed_channel_fraction": round(changed / (a.width * a.height * 3), 6),
            "psnr_db": round(10 * math.log10(255 ** 2 / mse), 4) if mse else 99.0}


def _gray_diff(a, b):
    _, ImageChops, ImageStat = _pillow()
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


def _scan(video, meta, executable, timeout, scan_size, ratio_threshold,
          min_change, luma_threshold):
    """Stream three small frames at a time; retain numeric series, never video."""
    Image, _, ImageStat = _pillow()
    scale = min(1, scan_size / max(meta["width"], meta["height"]))
    width, height = max(1, round(meta["width"] * scale)), max(1, round(meta["height"] * scale))
    process = subprocess.Popen([
        executable, "-nostdin", "-v", "error", "-i", str(video), "-map", "0:v:0",
        "-vf", f"scale={width}:{height}:flags=area,format=gray", "-fps_mode", "passthrough",
        "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    errors = deque(maxlen=8)

    def drain_errors():
        for line in iter(process.stderr.readline, b""):
            errors.append(line[-2000:])

    timed_out = threading.Event()

    def expire():
        timed_out.set()
        try:
            process.kill()
        except OSError:
            pass

    reader = threading.Thread(target=drain_errors, daemon=True)
    timer = threading.Timer(timeout, expire)
    reader.start()
    timer.start()
    previous = previous2 = None
    adjacent, across, luma = [], [], []
    try:
        while True:
            raw = process.stdout.read(width * height)
            if not raw:
                break
            if len(raw) != width * height:
                raise ValueError("FFmpeg returned a truncated raw frame")
            image = Image.frombytes("L", (width, height), raw)
            luma.append(ImageStat.Stat(image).mean[0])
            if previous is not None:
                adjacent.append(_gray_diff(image, previous))
            if previous2 is not None:
                across.append(_gray_diff(image, previous2))
            previous2, previous = previous, image
        process.wait()
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        timer.cancel()
        timer.join()
        process.stdout.close()
        reader.join()
        process.stderr.close()
    if timed_out.is_set():
        raise TimeoutError(f"FFmpeg scan timed out after {timeout}s")
    if process.returncode:
        raise ValueError("FFmpeg scan failed: " + b"".join(errors).decode("utf-8", "replace")[-2000:])
    if len(luma) != meta["frames"]:
        raise ValueError(f"Decoded frame count {len(luma)} differs from probe {meta['frames']}")
    floor = max(0.5, statistics.median(adjacent) * 0.25) if adjacent else 0.5
    flags, ratios = [], []
    for index in range(1, len(luma) - 1):
        before, after = adjacent[index - 1], adjacent[index]
        change = (before + after) / 2
        ratio = change / max(across[index - 1], floor)
        ratios.append(ratio)
        up, down = luma[index] - luma[index - 1], luma[index] - luma[index + 1]
        jump = min(abs(up), abs(down)) if up * down > 0 else 0.0
        # Both sides must change: an ordinary cut beside a hold is not flicker.
        if ((ratio > ratio_threshold and min(before, after) > min_change)
                or jump > luma_threshold):
            flags.append({"frame": index, "t": round(index / meta["fps"], 6),
                          "ratio": round(ratio, 4), "luma_jump": round(jump, 4),
                          "diff_before": round(before, 4), "diff_after": round(after, 4),
                          "diff_across": round(across[index - 1], 4)})
    return {"passed": not flags, "frames": len(luma), "interior_frames_checked": len(ratios),
            "scan_dimensions": [width, height], "noise_floor": round(floor, 4),
            "diff_mean": round(statistics.mean(adjacent), 4) if adjacent else 0.0,
            "diff_max": round(max(adjacent, default=0), 4),
            "ratio_max": round(max(ratios, default=0), 4), "flags": flags}


def _frame(video, index, meta, executable, timeout):
    Image, _, _ = _pillow()
    raw = _run([
        executable, "-nostdin", "-v", "error", "-i", str(video), "-map", "0:v:0",
        "-vf", f"select=eq(n\\,{index})", "-frames:v", "1", "-fps_mode", "passthrough",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ], timeout)
    if len(raw) != meta["width"] * meta["height"] * 3:
        raise ValueError(f"Could not decode render frame {index}")
    return Image.frombytes("RGB", (meta["width"], meta["height"]), raw)


def _snapshots(project, indices, meta, chrome, timeout, seek_mean):
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError as exc:
        raise Unavailable("Playwright unavailable; install it in the D:/ kit venv; "
                          "provide a local Chromium with --chrome or VIDEOKIT_CHROME") from exc
    Image, _, _ = _pillow()
    runtime = importlib.import_module(f"{__package__}.render" if __package__ else "render")
    executable = chrome or os.environ.get("VIDEOKIT_CHROME") or runtime.find_chrome()
    if executable and not Path(executable).is_file():
        raise Unavailable(f"Chromium unavailable: {executable}; use --chrome with an installed browser")
    forward, diagnostics = {}, []
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(executable_path=executable, headless=True,
                                                  timeout=timeout * 1000)
        except Error as exc:
            raise Unavailable(f"Chromium unavailable; use --chrome with a local executable: {exc}") from exc
        try:
            for reverse in (False, True):
                context = browser.new_context(viewport={"width": meta["width"], "height": meta["height"]},
                                              device_scale_factor=1)
                try:
                    page = context.new_page()
                    page.set_default_timeout(timeout * 1000)
                    page.add_init_script("window.__timelines = {};")
                    page.goto((project / "index.html").as_uri(), wait_until="networkidle")
                    page.evaluate("""async () => {
                        const root = document.querySelector('[data-composition-id="main"]');
                        if (!root) throw Error('Missing main composition');
                        root.style.width = root.dataset.width + 'px';
                        root.style.height = root.dataset.height + 'px';
                        await document.fonts.ready;
                        await Promise.all([...document.images].map(im => im.decode()));
                    }""")
                    size = page.evaluate("""() => {
                        const r = document.querySelector('[data-composition-id="main"]');
                        return [Number(r.dataset.width), Number(r.dataset.height)];
                    }""")
                    if size != [meta["width"], meta["height"]]:
                        raise ValueError(f"Composition dimensions {size} differ from render")
                    # Pre-seek to opposite ends in independent fresh contexts.
                    order = ([meta["frames"] - 1] + list(reversed(indices))) if reverse else [0] + indices
                    for position, index in enumerate(order):
                        result = page.evaluate(runtime.SEEK_JS, index / meta["fps"])
                        if result != "ok":
                            raise ValueError(f"Snapshot seek failed: {result}")
                        page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                        if position == 0:
                            continue
                        with Image.open(io.BytesIO(page.screenshot(type="png"))) as image:
                            image = image.convert("RGB")
                        if reverse:
                            metrics = image_metrics(forward[index], image)
                            diagnostics.append({"frame": index, "t": round(index / meta["fps"], 6),
                                                **metrics, "passed": metrics["mean_abs_diff"] <= seek_mean})
                        else:
                            forward[index] = image
                finally:
                    context.close()
        finally:
            browser.close()
    diagnostics.sort(key=lambda item: item["frame"])
    return forward, {"passed": all(item["passed"] for item in diagnostics), "samples": diagnostics}


def check_frames(project=None, *, render="out.mp4", times=None, flicker_only=False,
                 ffmpeg="ffmpeg", ffprobe="ffprobe", chrome=None, timeout=120,
                 scan_size=320, seek_mean=0.5, min_psnr=30.0, alignment_margin=0.2,
                 ratio_threshold=2.5, min_change=1.5, luma_threshold=6.0):
    """Return measured diagnostics without mutating project or render.

    times are seconds, snapped to the probed FPS grid; None chooses up to five
    unique interior samples. Requested samples outside the render are errors.
    Flicker covers interior frames only; first/last and persistent blanks need
    human review or snapshot parity. Fewer than three frames are explicitly
    reported as zero interior frames checked. Timeout is per engine operation.
    """
    report = {"status": "error", "passed": False, "seek_order": None,
              "render_vs_snapshot": None, "flicker": None}
    try:
        values = {"timeout": timeout, "scan_size": scan_size, "seek_mean": seek_mean,
                  "min_psnr": min_psnr, "alignment_margin": alignment_margin,
                  "ratio_threshold": ratio_threshold, "min_change": min_change,
                  "luma_threshold": luma_threshold}
        if any(not math.isfinite(value) or value <= 0 for value in values.values()):
            raise ValueError("Timeout, scan size and thresholds must be finite and positive")
        if int(scan_size) != scan_size:
            raise ValueError("scan_size must be an integer")
        base = Path(project).resolve() if project is not None else Path.cwd()
        video = Path(render)
        video = (base / video).resolve() if not video.is_absolute() else video.resolve()
        report.update(project=str(base) if project is not None else None, render=str(video), thresholds=values)
        if not video.is_file():
            raise ValueError(f"Render file does not exist: {video}")
        if not flicker_only and (project is None or not (base / "index.html").is_file()):
            raise ValueError("A project with index.html is required; use --flicker-only for video alone")
        engines = {name: shutil.which(command) for name, command in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe))}
        missing = [name for name, path in engines.items() if path is None]
        if missing:
            raise Unavailable(", ".join(missing) + " unavailable; install FFmpeg under D:/ and set PATH or --ffmpeg/--ffprobe")
        _pillow()
        meta = _probe(video, engines["ffprobe"], timeout)
        report["video"] = meta
        report["flicker"] = _scan(video, meta, engines["ffmpeg"], timeout, int(scan_size),
                                  ratio_threshold, min_change, luma_threshold)
        if not flicker_only:
            if abs(meta["fps"] - meta["nominal_fps"]) > 0.001:
                raise ValueError("Render/snapshot comparison requires constant-frame-rate video")
            if times is None:
                indices = sorted({int((meta["frames"] - 1) * part / 6) for part in range(1, 6)})
            else:
                requested = list(times)
                if not requested or any(not math.isfinite(t) or t < 0 for t in requested):
                    raise ValueError("times must contain finite, nonnegative seconds")
                indices = sorted({int(math.floor(t * meta["fps"] + 0.5)) for t in requested})
            if not indices or any(index < 0 or index >= meta["frames"] for index in indices):
                raise ValueError("Requested snapshot time is outside the decoded render frame range")
            snapshots, report["seek_order"] = _snapshots(base, indices, meta, chrome, timeout, seek_mean)
            comparisons = []
            for index in indices:
                neighbors = {}
                for offset in (-1, 0, 1):
                    if 0 <= index + offset < meta["frames"]:
                        neighbors[offset] = image_metrics(
                            snapshots[index], _frame(video, index + offset, meta, engines["ffmpeg"], timeout))
                exact = neighbors[0]
                best = max(neighbors, key=lambda offset: neighbors[offset]["psnr_db"])
                if neighbors[best]["psnr_db"] - exact["psnr_db"] <= alignment_margin:
                    best = 0
                comparisons.append({"frame": index, "t": round(index / meta["fps"], 6), **exact,
                                    "neighbor_psnr_db": {str(k): v["psnr_db"] for k, v in neighbors.items()},
                                    "best_offset": best, "passed": exact["psnr_db"] >= min_psnr and best == 0})
            report["render_vs_snapshot"] = {"passed": all(item["passed"] for item in comparisons),
                                             "samples": comparisons}
        checks = [report[name]["passed"] for name in ("seek_order", "render_vs_snapshot", "flicker")
                  if report[name] is not None]
        report.update(status="ok" if all(checks) else "failed", passed=all(checks))
    except Unavailable as exc:
        report.update(status="unavailable", message=str(exc))
    except Exception as exc:
        # Public result boundary also covers Playwright and image-decoder errors.
        # KeyboardInterrupt/SystemExit propagate after engine finally cleanup.
        report.update(status="error", message=str(exc))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", nargs="?")
    parser.add_argument("--render", default="out.mp4", help="absolute or relative to project")
    parser.add_argument("--times", help="comma-separated seconds; default: five unique frame samples")
    parser.add_argument("--flicker-only", action="store_true")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--chrome", help="local Chromium executable; no download")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--scan-size", type=int, default=320, help="longest scan dimension")
    parser.add_argument("--seek-mean", type=float, default=0.5)
    parser.add_argument("--min-psnr", type=float, default=30)
    parser.add_argument("--alignment-margin", type=float, default=0.2)
    parser.add_argument("--ratio-threshold", type=float, default=2.5)
    parser.add_argument("--min-change", type=float, default=1.5)
    parser.add_argument("--luma-threshold", type=float, default=6)
    parser.add_argument("--output", type=Path, help="optional new JSON file in an existing directory")
    args = parser.parse_args(argv)
    options = vars(args).copy()
    output = options.pop("output")
    try:
        options["times"] = [float(t) for t in args.times.split(",")] if args.times is not None else None
        # Exclusive creation prevents overwriting source, existing reports or symlinks.
        if output is not None and (output.exists() or not output.parent.is_dir()):
            raise ValueError("--output must be a new file in an existing directory")
        result = check_frames(**options)
        if output is not None:
            with output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    except (ValueError, OSError) as exc:
        result = {"status": "error", "passed": False, "message": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return {"ok": 0, "failed": 1, "error": 2, "unavailable": 3}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
