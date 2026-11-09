"""Offline agent-video-editor CC0 catalog audit and additive staging manifest.

Default: validate a caller-supplied checkout and print editor-assets-staging-v1
JSON without writing anything. --out explicitly writes ONE new manifest file;
--dry-run always prints JSON, including when --out is supplied. No assets are
downloaded, copied, decoded or installed. No kit library is opened or mutated.

Consumer contract: source_root + each files[].file locates the original bytes.
Recheck files[].sha256 before copying. id is namespaced; original_id is upstream.
Graphics have multiple files; file/sha256 alias the first file only. License
evidence is offline upstream testimony, not an independent legal verification.
SRC-CATALOG consumption is a separate Wave B integration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, urlsplit


SCHEMA = "editor-assets-staging-v1"
REPOSITORY = "https://github.com/kmilo93sd/agent-video-editor"
REVISION = "8e32c0aff64c445ef1e2b87bc04408a34d68c973"
BASE = "skills/editing-videos"
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
GRAPHIC_CATEGORIES = {
    "arrows", "highlights", "underlines", "focus", "callouts", "text",
    "progress", "status", "layouts", "overlays", "cta",
}


class UnavailableError(ValueError):
    """A local prerequisite is unavailable; no fallback is attempted."""


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def local_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"Invalid relative file: {relative!r}")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(x in ("", ".", "..") for x in relative.split("/")) or ":" in relative:
        raise ValueError(f"Unsafe relative file: {relative!r}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing file or path escapes source root: {relative}")
    if not path.stat().st_size:
        raise ValueError(f"Empty file: {relative}")
    return path


def git(root: Path, *args: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise UnavailableError("Git unavailable: install Git or put it on PATH; a local checkout is required")
    result = subprocess.run(
        [executable, "--no-optional-locks", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if result.returncode:
        raise ValueError(f"Local Git verification failed: {result.stderr.strip()}")
    return result.stdout.strip()


def blob_url(revision: str, file: str) -> str:
    return f"{REPOSITORY}/blob/{revision}/{quote(file, safe='/')}"


def read_catalog(root: Path, folder: str, version: int, key: str) -> tuple[dict, list]:
    relative = f"{BASE}/{folder}/catalog.json"
    path = local_file(root, relative)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != version:
        raise ValueError(f"Unsupported {folder} catalog version (expected {version})")
    rows = data.get(key)
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Missing/non-list/empty {folder} catalog {key}")
    return {"file": relative, "sha256": sha256(path), "version": version}, rows


def require(row: dict, keys: tuple[str, ...]) -> None:
    if not isinstance(row, dict):
        raise ValueError("Catalog entry must be an object")
    for key in keys:
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError(f"{row.get('id', '?')}: missing/invalid {key}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", row["id"]):
        raise ValueError(f"Invalid original ID: {row['id']}")
    if row.get("attribution_required") is not False:
        raise ValueError(f"{row['id']}: missing or conflicting CC0 attribution evidence")


def evidence(root: Path, folder: str, revision: str) -> tuple[dict, str]:
    relative = f"{BASE}/{folder}/LICENSES.md"
    path = local_file(root, relative)
    text = path.read_text(encoding="utf-8")
    # The declaration, legal URL and per-entry relationship are all required.
    declaration = text.split("## ", 1)[0]
    if not re.search(r"CC0[ -]1\.0", declaration) or CC0 not in declaration:
        raise ValueError(f"Missing CC0 license evidence declaration/legal URL: {relative}")
    return {"file": relative, "source_url": blob_url(revision, relative),
            "sha256": sha256(path), "declaration": declaration.strip()}, text


def audio_evidence(row: dict, document: dict, text: str) -> dict:
    original = row["source_url"]
    generated = original.startswith(("generated with ffmpeg", "generated for this library (tools/synthesize.py"))
    if generated:
        section = text.split("## Generated here:", 1)
        if len(section) != 2:
            raise ValueError(f"{row['id']}: missing generated-source license evidence")
        section = section[1].split("## ", 1)[0]
        matches = [line for line in section.splitlines() if f"`{row['id']}`" in line]
    else:
        parsed = urlsplit(original)
        if parsed.scheme != "https" or not parsed.netloc or any(c.isspace() for c in original):
            raise ValueError(f"{row['id']}: invalid source URL")
        # Require the exact source in a table row, not an excluded-source mention.
        matches = [line for line in text.splitlines() if line.startswith("| ")
                   and any(cell.strip() == original for cell in line.split("|"))]
    if not matches:
        raise ValueError(f"{row['id']}: missing per-asset license evidence for {original}")
    return {**document, "matched_by": "original_id" if generated else "source_url",
            "excerpt": "\n".join(matches)}


def build_manifest(source_root: Path, revision: str = REVISION, subset: str = "all",
                   ids: list[str] | None = None) -> dict:
    root = source_root.resolve()
    if not root.is_dir():
        raise UnavailableError(f"Source checkout unavailable: {root}; supply --source-root (no automatic download)")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("--revision must be a full immutable lowercase Git SHA")
    if git(root, "rev-parse", "--show-toplevel").replace("\\", "/").lower() != root.as_posix().lower():
        raise ValueError("--source-root must be the checkout root")
    if git(root, "rev-parse", "HEAD") != revision:
        raise ValueError("Source HEAD differs from --revision; use the reviewed pinned checkout")
    if git(root, "status", "--porcelain", "--untracked-files=all", "--", f"{BASE}/library", f"{BASE}/graphics"):
        raise ValueError("Source catalogs/assets/evidence have uncommitted changes; provenance cannot be pinned")

    assets, catalogs = [], []
    for folder, version, key in (("library", 2, "sounds"), ("graphics", 1, "assets")):
        descriptor, rows = read_catalog(root, folder, version, key)
        catalogs.append(descriptor)
        document, license_text = evidence(root, folder, revision)
        seen_ids, seen_files = set(), set()
        for row in rows:
            require(row, ("id", "category", "license", "source_url", "origin", "suggested_use") if folder == "library"
                    else ("id", "category", "license", "source", "description", "call"))
            if row["id"] in seen_ids:
                raise ValueError(f"Duplicate {folder} original ID: {row['id']}")
            seen_ids.add(row["id"])
            expected_license = "CC0 1.0" if folder == "library" else "CC0-1.0"
            if row["license"] != expected_license:
                raise ValueError(f"{row['id']}: unsupported or conflicting license {row['license']}")
            if folder == "library":
                files = [row.get("file")]
                duration = row.get("duration_s")
                if type(duration) not in (int, float) or not math.isfinite(duration) or duration <= 0:
                    raise ValueError(f"{row['id']}: invalid duration_s")
                for metric in ("lufs", "true_peak_dbtp"):
                    if type(row.get(metric)) not in (int, float) or not math.isfinite(row[metric]):
                        raise ValueError(f"{row['id']}: missing/invalid catalog {metric}")
                license_evidence = audio_evidence(row, document, license_text)
            else:
                files = row.get("files")
                if row["category"] not in GRAPHIC_CATEGORIES or not row["source"].startswith("Original work for this repository"):
                    raise ValueError(f"{row['id']}: missing original-graphics license evidence")
                if "Every asset in this folder" not in document["declaration"] or "written by hand" not in document["declaration"]:
                    raise ValueError(f"{row['id']}: missing graphics blanket dedication evidence")
                license_evidence = {**document, "matched_by": "original_graphics_dedication",
                                    "excerpt": document["declaration"]}
            if not isinstance(files, list) or not files:
                raise ValueError(f"{row['id']}: missing files")
            staged_files = []
            for file in files:
                if not isinstance(file, str):
                    raise ValueError(f"{row['id']}: invalid file")
                path = local_file(root / BASE / folder, file)
                category = PurePosixPath(file).parts[0]
                if folder == "library":
                    allowed = category in ("sfx", "music") and path.suffix in (".wav", ".mp3")
                else:
                    allowed = category == row["category"] and path.suffix in (".html", ".svg")
                if not allowed or file.casefold() in seen_files:
                    raise ValueError(f"{row['id']}: unsupported/duplicate asset file: {file}")
                seen_files.add(file.casefold())
                relative = f"{BASE}/{folder}/{file}"
                staged_files.append({"file": relative, "sha256": sha256(path),
                                     "bytes": path.stat().st_size, "source_url": blob_url(revision, relative)})
            primary = staged_files[0]
            original_source = row["source_url"] if folder == "library" else row["source"]
            assets.append({
                "id": f"agent-video-editor.{'audio' if folder == 'library' else 'graphics'}.{row['id']}",
                "original_id": row["id"], "kind": "audio" if folder == "library" else "graphics",
                "category": row["category"], "file": primary["file"], "sha256": primary["sha256"],
                "files": staged_files, "source_url": original_source if original_source.startswith("https://") else primary["source_url"],
                "origin": row.get("origin", row.get("source")), "source_description": original_source,
                "license": "CC0-1.0", "license_url": CC0, "attribution_required": False,
                "license_evidence": license_evidence, "upstream": row,
            })
        # Include only cataloged assets, and reject unaccounted-for files in asset folders.
        categories = ("sfx", "music") if folder == "library" else GRAPHIC_CATEGORIES
        disk_files = {p.relative_to(root / BASE / folder).as_posix().casefold()
                      for category in categories for p in (root / BASE / folder / category).rglob("*") if p.is_file()}
        if disk_files != seen_files:
            raise ValueError(f"{folder}: catalog/files disagree: {sorted(disk_files ^ seen_files)}")

    # Validate both full catalogs before selecting the requested additive subset.
    wanted = set(ids or [])
    known = {row["id"] for row in assets}
    if wanted - known:
        raise ValueError(f"Unknown namespaced asset IDs: {sorted(wanted - known)}")
    assets = [row for row in assets if (subset == "all" or row["kind"] == subset)
              and (not wanted or row["id"] in wanted)]
    if not assets:
        raise ValueError("Selection contains no assets")
    return {"schema": SCHEMA, "mode": "additive", "provider": "agent-video-editor",
            "repository": REPOSITORY, "revision": revision, "source_root": root.as_posix(),
            "catalogs": catalogs, "assets": assets,
            "validation": {"catalogs": 2, "selected_assets": len(assets),
                           "selected_files": sum(len(a["files"]) for a in assets),
                           "offline": True, "media_decoded": False}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-root", required=True, type=Path, help="Existing local agent-video-editor Git checkout")
    parser.add_argument("--revision", default=REVISION, help="Reviewed full source SHA; default is research pin")
    parser.add_argument("--subset", choices=("all", "audio", "graphics"), default="all")
    parser.add_argument("--id", action="append", help="Select namespaced asset ID (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print JSON; suppress --out writes")
    parser.add_argument("--out", type=Path, help="Create only this NEW manifest; parent must exist, never overwrite")
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args.source_root, args.revision, args.subset, args.id)
        payload = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.out is not None and not args.dry_run:
            if args.out.is_symlink():
                raise ValueError("--out must be a new regular file, not a symlink")
            target = args.out.resolve()
            kit = Path(__file__).resolve().parent.parent
            source = args.source_root.resolve()
            if target.is_relative_to(kit) or target.is_relative_to(source):
                raise ValueError("--out must be outside the kit and source checkout; use a staging/cache folder")
            # Exclusive creation also refuses existing files and symlinks.
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
            print(json.dumps({"status": "ok", "schema": SCHEMA, "manifest": str(target),
                              "assets": len(manifest["assets"])}))
        else:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            print(payload, end="")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        status = "unavailable" if isinstance(exc, UnavailableError) else "error"
        print(json.dumps({"status": status, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
