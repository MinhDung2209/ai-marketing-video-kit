"""Caption wiring: timing.json estimates, aligned words, and authored VTT/SRT.

build(path, max_chars=46) returns a cue array; build_track returns timing
provenance, source words, cues and layout warnings. No speech engine runs here.
Aligned words are {text,start,end} in timeline seconds, never line-relative.
lines[].caption wins verbatim over aligned/spoken text; an empty caption hides
the line. --voice reads caption overrides by line id without changing voice.json.
--overrides uses inclusive word_start/word_end ranges from caption_layout.
Conflicting corrections fail. --caption-track is authoritative (text AND times,
IDs/settings/markup); it is never regenerated from alignment. All inputs are
read-only. --aspect enables two-line 16:9/9:16 layout; no words means estimated.

  python -B tools/captions.py timing.json --aligned-words words.json --aspect 9:16 --format json
  python -B tools/captions.py timing.json --voice voice.json --format vtt
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import re
import sys

if __package__:
    from . import caption_layout, caption_vtt
else:
    import caption_layout
    import caption_vtt

TAG = re.compile(r"\[(short|medium|long) pause\]|\[[a-z ]+\]")


def split_line(text, max_chars):
    """Keep the established estimated splitting for uncorrected text."""
    parts = [p.strip() for p in re.split(r"\[(?:short|medium|long) pause\]", text)]
    out = []
    for p in parts:
        p = TAG.sub("", p).replace("...", "…").strip()
        if not p:
            continue
        p = " ".join(w.lower() if len(w) >= 4 and w.isupper() else w for w in p.split(" "))
        while len(p) > max_chars:
            mid = len(p) // 2
            commas = [i for i, ch in enumerate(p) if ch == "," and 8 <= i <= len(p) - 8]
            if commas:
                cut = min(commas, key=lambda i: abs(i - mid))
            else:
                spaces = [i for i, ch in enumerate(p) if ch == " " and 6 <= i <= len(p) - 6]
                if not spaces:
                    break
                cut = min(spaces, key=lambda i: abs(i - mid))
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    return out


def _load(value):
    if isinstance(value, (str, Path)):
        return json.loads(Path(value).read_text(encoding="utf-8-sig"))
    return deepcopy(value)


def _seconds(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite seconds")
    return float(value)


def _lines(timing, voice):
    if not isinstance(timing, dict) or not isinstance(timing.get("lines"), list):
        raise ValueError("timing requires a lines array")
    lines = deepcopy(timing["lines"])
    if any(not isinstance(line, dict) for line in lines):
        raise ValueError("timing lines must be objects")
    if voice is not None:
        script = _load(voice)
        if not isinstance(script, dict) or not isinstance(script.get("lines"), list):
            raise ValueError("voice requires a lines array")
        corrections = {}
        for line in script["lines"]:
            if not isinstance(line, dict) or not isinstance(line.get("id"), str):
                raise ValueError("voice lines require string ids")
            if line["id"] in corrections:
                raise ValueError("voice line ids must be unique")
            corrections[line["id"]] = line
        for line in lines:
            source = corrections.get(line.get("id"), {})
            if "caption" in source:
                line["caption"] = source["caption"]
    previous = 0.0
    for index, line in enumerate(lines):
        start = _seconds(line.get("start"), f"line {index} start")
        duration = _seconds(line.get("dur"), f"line {index} dur")
        if start + 1e-9 < previous or duration <= 0:
            raise ValueError(f"line {index} must be ordered, nonoverlapping and positive-duration")
        for field in ("text", "caption"):
            if field in line and not isinstance(line[field], str):
                raise ValueError(f"line {index} {field} must be a string")
        line.update(start=start, dur=duration)
        previous = start + duration
    return lines


def _authored_track(value):
    if isinstance(value, (str, Path)) and Path(value).suffix.lower() in {".vtt", ".srt"}:
        path = Path(value)
        reader = caption_vtt.read_vtt if path.suffix.lower() == ".vtt" else caption_vtt.read_srt
        track = reader(path.read_text(encoding="utf-8-sig"))
    else:
        track = _load(value)
    caption_vtt.write_vtt(track)  # Validate without rewriting authored cue data.
    return dict(track, status="ok", timing="authored", words=[], warnings=[])


def build_track(timing_path, max_chars=46, *, aligned_words=None, aspect=None,
                overrides=None, voice=None, caption_track=None):
    """Read only; missing alignment estimates, invalid supplied alignment fails.

    Words must fit timing line bounds (1 ms rounding tolerance). Corrected display
    text is marked estimated even when its underlying spoken words are aligned.
    """
    if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    if aspect not in {None, "16:9", "9:16"}:
        raise ValueError("aspect must be 16:9 or 9:16")
    if caption_track is not None:
        if overrides is not None or voice is not None:
            raise ValueError("caption_track is authoritative; supply corrections in that track")
        return _authored_track(caption_track)
    lines = _lines(_load(timing_path), voice)
    extra = [] if overrides is None else _load(overrides)
    if not isinstance(extra, list):
        raise ValueError("overrides must be an array")
    # Preserve original character-weighted cue timing without a layout request.
    if aligned_words is None and aspect is None and not extra:
        cues = []
        for line in lines:
            manual = "caption" in line
            if manual:
                chunks = [line["caption"]] if line["caption"].strip() else []
            else:
                chunks = split_line(line.get("text", ""), max_chars)
            total = sum(map(len, chunks)) or 1
            start = line["start"]
            for chunk in chunks:
                end = start + line["dur"] * len(chunk) / total
                cues.append({"start": round(start, 2), "end": round(end, 2), "text": chunk,
                             "timing": "estimated", "manual": manual})
                start = end
        return {"status": "ok", "timing": "estimated", "words": [], "cues": cues, "warnings": []}
    timing = "aligned" if aligned_words is not None else "estimated"
    if aligned_words is not None:
        payload = _load(aligned_words)
        if isinstance(payload, dict):
            if payload.get("timing", "aligned") != "aligned" or payload.get("status", "ok") != "ok":
                raise ValueError("aligned_words requires successful aligned timing")
            embedded = payload.get("overrides", [])
            if not isinstance(embedded, list):
                raise ValueError("aligned word overrides must be an array")
            extra = embedded + extra
            payload = payload.get("words")
        words = caption_layout._validate_words(payload)
    else:
        words = []
        for line_index, line in enumerate(lines):
            tokens = " ".join(split_line(line.get("text", ""), sys.maxsize)).split()
            if not tokens and line.get("caption", "").strip():
                tokens = line["caption"].split()
            total = sum(map(len, tokens)) or 1
            start = line["start"]
            for index, token in enumerate(tokens):
                end = start + line["dur"] * len(token) / total
                if index == len(tokens) - 1:
                    end = line["start"] + line["dur"]
                    if line_index + 1 < len(lines):
                        end = min(end, lines[line_index + 1]["start"])
                words.append({"text": token, "start": start, "end": end})
                start = end
    manual, suppressed = [], []
    cursor = 0
    for line_index, line in enumerate(lines):
        first = cursor
        end = line["start"] + line["dur"]
        boundary = min(end, lines[line_index + 1]["start"]) if line_index + 1 < len(lines) else end
        while cursor < len(words) and words[cursor]["start"] < boundary:
            word = words[cursor]
            if word["start"] < line["start"] - 0.001 or word["end"] > end + 0.001:
                raise ValueError("Aligned words must fit timing line bounds; check timeline offsets")
            cursor += 1
        if first == cursor:
            if TAG.sub("", line.get("text", "")).strip() or line.get("caption", "").strip():
                raise ValueError("A captioned/spoken line has no aligned words; omit aligned_words to estimate")
            continue
        words[first]["break_before"] = True
        if "caption" in line:
            if line["caption"].strip():
                manual.append({"word_start": first, "word_end": cursor - 1, "text": line["caption"]})
            else:
                suppressed.append((first, cursor - 1))
    if cursor != len(words):
        raise ValueError("Aligned words extend beyond timing lines")
    rules = None if aspect else replace(caption_layout.LayoutRules(), max_chars_per_line=max_chars,
                                       min_duration=0, max_hold=0)
    duration = max(lines[-1]["start"] + lines[-1]["dur"] if lines else 0,
                   words[-1]["end"] if words else 0)
    result = caption_layout.layout(words, timing=timing, aspect=aspect or "16:9",
                                   duration=duration, overrides=manual + extra, rules=rules)
    if any(a <= item["word_end"] and item["word_start"] <= b
           for a, b in suppressed for item in extra):
        raise ValueError("Word override conflicts with an explicitly hidden line caption")
    hidden = {i for i, cue in enumerate(result["cues"]) if any(
        a <= cue["word_start"] <= cue["word_end"] <= b for a, b in suppressed)}
    visible = [i for i in range(len(result["cues"])) if i not in hidden]
    indices = {old: new for new, old in enumerate(visible)}
    result["warnings"] = [dict(w, cue=indices[w["cue"]]) for w in result["warnings"] if w["cue"] in indices]
    result["cues"] = [result["cues"][i] for i in visible]
    return result


def build(timing_path, max_chars=46, **options):
    """Return the established list shape, with timing/manual metadata added."""
    return build_track(timing_path, max_chars, **options)["cues"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timing", type=Path)
    parser.add_argument("max_chars", type=int, nargs="?", default=46)
    parser.add_argument("--aligned-words", type=Path)
    parser.add_argument("--aspect", choices=["16:9", "9:16"])
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--voice", type=Path)
    parser.add_argument("--caption-track", type=Path)
    parser.add_argument("--format", choices=["display", "json", "vtt", "srt"], default="display")
    args = parser.parse_args(argv)
    try:
        track = build_track(args.timing, args.max_chars, aligned_words=args.aligned_words,
                            aspect=args.aspect, overrides=args.overrides, voice=args.voice,
                            caption_track=args.caption_track)
        if args.format == "json":
            print(json.dumps(track, ensure_ascii=False, allow_nan=False, indent=2))
        elif args.format in {"vtt", "srt"}:
            writer = caption_vtt.write_vtt if args.format == "vtt" else caption_vtt.write_srt
            print(writer(track), end="")
        else:
            for cue in track["cues"]:
                print(f'{cue["start"]:6.2f} → {cue["end"]:6.2f}  {cue["text"]}')
            print(f'timing={track["timing"]}', file=sys.stderr)
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
