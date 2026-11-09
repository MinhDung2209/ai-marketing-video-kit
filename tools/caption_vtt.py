"""Loss-aware WebVTT/SRT sidecars; no speech engine or network dependency.

The track dictionary follows OpenFilm's caption concepts: header, notes,
regions, styles, and cues with {id, start, end, settings, text}. Times are seconds.
Payloads remain authored strings, including emphasis, entities, inline times,
Unicode and whitespace. No splitting, deduplication or word timing is performed.
VTT block order/line endings and timestamp spelling are canonicalized on output.

Python: read_vtt(text), write_vtt(track), read_srt(text, metadata=None),
write_srt(track, allow_lossy=False), srt_metadata(track).
SRT cannot carry VTT settings or arbitrary IDs. Use the explicit metadata JSON
sidecar for a lossless conversion. Metadata never contains caption text/times,
so subsequent manual SRT corrections remain authoritative. Without metadata,
an export that loses information fails unless allow_lossy=True is explicit.

CLI (UTF-8; output must be new unless --force is supplied)::

    python tools/caption_vtt.py import captions.vtt -o track.json
    python tools/caption_vtt.py export track.json -o captions.vtt
    python tools/caption_vtt.py convert captions.vtt -o captions.srt --metadata captions.meta.json
    python tools/caption_vtt.py convert captions.srt -o restored.vtt --metadata captions.meta.json

Concept reference: OpenFilm src/captions.mjs at a85a80a97429 (MIT).
This is an independent Python implementation, without its renderer/Studio code.
"""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import re
import sys


_TIME = r"(?:(?:[0-9]{2,}):)?[0-9]{2}:[0-9]{2}[.,][0-9]{1,3}"
_TIMING = re.compile(
    rf"^(?P<start>{_TIME})[ \t]+-->[ \t]+(?P<end>{_TIME})"
    r"(?:[ \t](?P<settings>[^\r\n]*))?$"
)
_META_SCHEMA = "caption-vtt-srt-metadata-v1"
_BLOCK_FIELDS = ("notes", "regions", "styles")


class CaptionError(ValueError):
    """Invalid captions or a conversion that would silently lose information."""


def _new_track() -> dict:
    return {"header": "WEBVTT", "notes": [], "regions": [], "styles": [], "cues": []}


def timestamp_seconds(value: str) -> float:
    """Parse an MM:SS.mmm / HH:MM:SS.mmm timestamp (comma also accepted)."""
    if not isinstance(value, str) or not re.fullmatch(_TIME, value):
        raise CaptionError(f"Invalid timestamp: {value!r}")
    parts = value.replace(",", ".").split(":")
    hours, minutes, seconds = (0, *parts) if len(parts) == 2 else parts
    if int(minutes) >= 60 or Decimal(seconds) >= 60:
        raise CaptionError(f"Timestamp minutes/seconds out of range: {value!r}")
    return float(int(hours) * 3600 + int(minutes) * 60 + Decimal(seconds))


def _milliseconds(seconds: float) -> int:
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float, Decimal)):
        raise CaptionError(f"Time must be a finite nonnegative number: {seconds!r}")
    try:
        value = Decimal(str(seconds))
        if not value.is_finite() or value < 0:
            raise CaptionError(f"Time must be finite and nonnegative: {seconds!r}")
        return int((value * 1000).to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation, OverflowError) as exc:
        raise CaptionError(f"Invalid time: {seconds!r}") from exc


def timestamp_text(seconds: float, *, srt: bool = False) -> str:
    """Canonical timestamp, rounded once to milliseconds without clamping."""
    hours, remainder = divmod(_milliseconds(seconds), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{',' if srt else '.'}{millis:03}"


def _text(value: object, name: str, *, single: bool = False) -> str:
    if not isinstance(value, str) or "\r" in value or "\x00" in value:
        raise CaptionError(f"{name} must be a string with LF line endings and no NUL")
    if single and "\n" in value:
        raise CaptionError(f"{name} must be one line")
    return value


def _no_blank_lines(value: str, name: str) -> None:
    if value and any(not line.strip(" \t") for line in value.split("\n")):
        raise CaptionError(f"{name} contains a blank line, which terminates a caption block")


def validate_track(track: dict) -> dict:
    """Validate without changing text or order; default absent optional fields."""
    if not isinstance(track, dict) or not isinstance(track.get("cues"), list):
        raise CaptionError("Track must be an object with a cues array")
    out = copy.deepcopy(track)
    header = _text(out.setdefault("header", "WEBVTT"), "header")
    if not re.fullmatch(r"WEBVTT(?:[ \t][^\n]*)?(?:\n[^\n]+)*", header) or "-->" in header:
        raise CaptionError("Header must start with WEBVTT and contain no blank lines/arrows")
    _no_blank_lines(header, "header")
    for field in _BLOCK_FIELDS:
        blocks = out.setdefault(field, [])
        if not isinstance(blocks, list):
            raise CaptionError(f"{field} must be an array of strings")
        for block in blocks:
            _text(block, field)
            _no_blank_lines(block, field)
            if field == "notes" and not re.match(r"^NOTE(?:[ \t\n]|$)", block):
                raise CaptionError("Each note must start with NOTE")
    for index, cue in enumerate(out["cues"], 1):
        if not isinstance(cue, dict):
            raise CaptionError(f"Cue {index} must be an object")
        for field in ("id", "settings", "text"):
            value = _text(cue.setdefault(field, ""), f"cue {index} {field}", single=field != "text")
            if field == "text":
                _no_blank_lines(value, f"cue {index} text")
            elif "-->" in value:
                raise CaptionError(f"Cue {index} {field} contains a timing arrow")
        if cue["id"] and re.match(r"^(?:NOTE(?:[ \t]|$)|STYLE$|REGION$)", cue["id"]):
            raise CaptionError(f"Cue {index} ID conflicts with a WebVTT block marker")
        if "start" not in cue or "end" not in cue:
            raise CaptionError(f"Cue {index} requires start and end times")
        if _milliseconds(cue["end"]) <= _milliseconds(cue["start"]):
            raise CaptionError(f"Cue {index} must end after start at millisecond precision")
    return out


def _blocks(text: str) -> list[list[str]]:
    if not isinstance(text, str):
        raise CaptionError("Caption source must be a string")
    text = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if "\x00" in text:
        raise CaptionError("Caption source contains NUL; expected UTF-8 text")
    blocks: list[list[str]] = []
    block: list[str] = []
    for line in text.split("\n"):
        if line.strip(" \t"):
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)
    return blocks


def _cue(block: list[str], number: int) -> dict:
    at = 0 if _TIMING.fullmatch(block[0]) else 1
    match = _TIMING.fullmatch(block[at]) if at < len(block) else None
    if match is None:
        raise CaptionError(f"Block {number}: expected an optional ID then a timing line")
    payload = block[at + 1:]
    if any(_TIMING.fullmatch(line) for line in payload):
        raise CaptionError(f"Block {number}: timing line inside payload; separate cues with a blank line")
    return {
        "id": block[0] if at else "",
        "start": timestamp_seconds(match["start"]),
        "end": timestamp_seconds(match["end"]),
        "settings": match["settings"] or "",
        "text": "\n".join(payload),
    }


def read_vtt(text: str) -> dict:
    """Read a VTT track, including header metadata, NOTE/REGION/STYLE blocks.

    Invalid/unknown blocks fail explicitly instead of dropping authored captions.
    Adjacent/overlapping cues are kept separately in their authored order.
    """
    blocks = _blocks(text)
    if not blocks or not re.fullmatch(r"WEBVTT(?:[ \t].*)?", blocks[0][0]):
        raise CaptionError("WebVTT input requires a WEBVTT header and blank line before cues")
    out = _new_track()
    out["header"] = "\n".join(blocks[0])
    for number, block in enumerate(blocks[1:], 2):
        if re.match(r"^NOTE(?:[ \t]|$)", block[0]):
            out["notes"].append("\n".join(block))
        elif block[0] in ("REGION", "STYLE"):
            out["regions" if block[0] == "REGION" else "styles"].append("\n".join(block[1:]))
        else:
            out["cues"].append(_cue(block, number))
    return validate_track(out)


def _cue_text(cue: dict, *, srt: bool = False, cue_id: str | None = None) -> str:
    cue_id = cue["id"] if cue_id is None else cue_id
    timing = f"{timestamp_text(cue['start'], srt=srt)} --> {timestamp_text(cue['end'], srt=srt)}"
    if not srt and cue["settings"]:
        timing += " " + cue["settings"]
    return (cue_id + "\n" if cue_id else "") + timing + "\n" + cue["text"]


def write_vtt(track: dict) -> str:
    """Serialize without regenerating, flattening or trimming cue text."""
    track = validate_track(track)
    # A literal timing line would be ambiguous with a missing cue separator.
    if any(_TIMING.fullmatch(line) for cue in track["cues"] for line in cue["text"].split("\n")):
        raise CaptionError("Cue text contains an ambiguous literal timing line")
    blocks = [track["header"], *track["notes"]]
    blocks += ["REGION\n" + block for block in track["regions"]]
    blocks += ["STYLE\n" + block for block in track["styles"]]
    blocks += [_cue_text(cue) for cue in track["cues"]]
    return "\n\n".join(blocks) + "\n\n"


def srt_losses(track: dict) -> list[str]:
    """Fields that plain SRT cannot preserve; an explicit sidecar retains them."""
    track = validate_track(track)
    losses = [field for field in _BLOCK_FIELDS if track[field]]
    if track["header"] != "WEBVTT":
        losses.append("header")
    if any(cue["settings"] for cue in track["cues"]):
        losses.append("cue settings")
    if any(not re.fullmatch(r"[0-9]+", cue["id"]) for cue in track["cues"]):
        losses.append("cue IDs")
    return losses


def srt_metadata(track: dict) -> dict:
    """Build a companion for SRT exported with canonical numeric IDs.

    No caption words or times are stored: edits in the SRT always win. Changing
    its cue count/IDs requires a new companion; stale companions fail explicitly.
    """
    track = validate_track(track)
    return {
        "schema": _META_SCHEMA,
        "track": {key: track[key] for key in ("header", *_BLOCK_FIELDS)},
        "cues": [{"srt_id": str(i), "id": cue["id"], "settings": cue["settings"]}
                 for i, cue in enumerate(track["cues"], 1)],
    }


def write_srt(track: dict, *, allow_lossy: bool = False, metadata: bool = False) -> str:
    """Write standard SRT with raw markup/Unicode payloads.

    metadata=True numbers cues 1..N; caller must retain srt_metadata(track).
    SRT player support for WebVTT-specific payload tags varies; their bytes are
    retained, not converted into a different markup dialect.
    """
    track = validate_track(track)
    losses = srt_losses(track)
    if losses and not (allow_lossy or metadata):
        raise CaptionError("SRT cannot retain " + ", ".join(losses) + "; use --metadata or --allow-lossy")
    if any(_TIMING.fullmatch(line) for cue in track["cues"] for line in cue["text"].split("\n")):
        raise CaptionError("Cue text contains an ambiguous literal timing line")
    blocks = [_cue_text(cue, srt=True, cue_id=(str(i) if metadata or "cue IDs" in losses else cue["id"]))
              for i, cue in enumerate(track["cues"], 1)]
    return "\n\n".join(blocks) + ("\n\n" if blocks else "")


def read_srt(text: str, metadata: dict | None = None) -> dict:
    """Read SRT, keeping raw text, numeric IDs and optional timing extensions."""
    out = _new_track()
    for number, block in enumerate(_blocks(text), 1):
        cue = _cue(block, number)
        if not re.fullmatch(r"[0-9]+", cue["id"]):
            raise CaptionError(f"SRT block {number} requires a numeric cue ID")
        out["cues"].append(cue)
    if metadata is not None:
        if not isinstance(metadata, dict) or metadata.get("schema") != _META_SCHEMA:
            raise CaptionError("Unrecognized SRT metadata schema")
        entries, track = metadata.get("cues"), metadata.get("track")
        if not isinstance(entries, list) or not isinstance(track, dict):
            raise CaptionError("SRT metadata requires track and cues")
        if any(not isinstance(entry, dict) or not all(isinstance(entry.get(k), str)
               for k in ("srt_id", "id", "settings")) for entry in entries):
            raise CaptionError("Invalid cue entry in SRT metadata")
        by_id = {entry["srt_id"]: entry for entry in entries}
        ids = [cue["id"] for cue in out["cues"]]
        if len(by_id) != len(entries) or len(set(ids)) != len(ids) or set(ids) != set(by_id):
            raise CaptionError("SRT cue IDs/count do not match metadata; refresh the companion")
        for key in ("header", *_BLOCK_FIELDS):
            if key not in track:
                raise CaptionError(f"SRT metadata missing {key}")
            out[key] = copy.deepcopy(track[key])
        for cue in out["cues"]:
            entry = by_id[cue["id"]]
            if cue["settings"] and cue["settings"] != entry["settings"]:
                raise CaptionError("SRT timing settings conflict with companion metadata")
            cue.update(id=entry["id"], settings=entry["settings"])
    return validate_track(out)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def _format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in (".vtt", ".srt", ".json"):
        raise CaptionError("Use a .vtt, .srt or .json filename")
    return suffix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("import", "export", "convert"))
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--metadata", type=Path, help="SRT companion: read for SRT input, write for SRT output")
    parser.add_argument("--allow-lossy", action="store_true", help="Explicitly discard SRT-inexpressible fields")
    parser.add_argument("--force", action="store_true", help="Allow replacement of existing output files")
    args = parser.parse_args(argv)
    try:
        src, dst = _format(args.input), _format(args.output)
        if args.command == "import" and (src == ".json" or dst != ".json"):
            raise CaptionError("import requires VTT/SRT input and JSON output")
        if args.command == "export" and (src != ".json" or dst == ".json"):
            raise CaptionError("export requires JSON input and VTT/SRT output")
        if args.metadata and (src == dst == ".srt" or ".srt" not in (src, dst)):
            raise CaptionError("--metadata requires exactly one SRT endpoint")
        paths = [args.input.resolve(), args.output.resolve()]
        if args.metadata:
            paths.append(args.metadata.resolve())
        if len(set(paths)) != len(paths):
            raise CaptionError("Input, output and metadata must be distinct paths")
        outputs = [args.output] + ([args.metadata] if args.metadata and dst == ".srt" else [])
        for path in outputs:
            if path.exists() and not args.force:
                raise CaptionError(f"Output already exists: {path}; use --force to replace it")
            if not path.parent.is_dir():
                raise CaptionError(f"Output parent directory does not exist: {path.parent}")
        if src == ".json":
            track = validate_track(_read_json(args.input))
        else:
            text = args.input.read_text(encoding="utf-8-sig")
            track = read_vtt(text) if src == ".vtt" else read_srt(
                text, _read_json(args.metadata) if args.metadata else None)
        losses = srt_losses(track) if dst == ".srt" else []
        if dst == ".json":
            rendered = _json_text(track)
        elif dst == ".vtt":
            rendered = write_vtt(track)
        else:
            rendered = write_srt(track, allow_lossy=args.allow_lossy, metadata=bool(args.metadata))
        # Compute all content before creating outputs, and avoid replacing human edits by default.
        if args.metadata and dst == ".srt":
            meta_text = _json_text(srt_metadata(track))
            with args.metadata.open("w" if args.force else "x", encoding="utf-8", newline="\n") as handle:
                handle.write(meta_text)
        with args.output.open("w" if args.force else "x", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
        result = {"status": "ok", "output": str(args.output.resolve()), "cues": len(track["cues"])}
        if args.metadata:
            result["metadata"] = str(args.metadata.resolve())
        if losses and not args.metadata:
            result["discarded"] = losses
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (CaptionError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
