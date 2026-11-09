"""Refresh the audio catalog additively, preserving existing IDs, paths and metadata.

Legacy sources: HyperFrames/Pixabay, attributed video-shotcraft/Mixkit and uisfx
(including the kit-local fallback). No downloads or source-pin changes are made.

Usage: python tools/build_library.py --repos _repos --out kit/audio-library
       --manifest PROJECT/public/audio/sfx/audio-manifest.json

Repeat --manifest for video-shotcraft v1 Freesound manifests. Files are relative
to each manifest. SHA-256, audio and commercial license evidence are validated
before copying. CC BY requires --freesound-license by; attribution metadata and
the complete original row are retained in the catalog for publication credits.
Different bytes for an existing Freesound ID are a conflict, never an overwrite.
AUDIO-CC0 staging manifests are not consumed here (Wave B interface pending).
"""

import argparse
import hashlib
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def local_path(root, relative):
    """Reject absolute paths, traversal and symlinks escaping the source root."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"Invalid relative asset path: {relative!r}")
    path = pathlib.PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or ":" in relative:
        raise ValueError(f"Invalid relative asset path: {relative!r}")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"Asset escapes its directory: {relative!r}")
    return result


def duration(path, required=False):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=codec_type:format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=30,
        )
        info = json.loads(result.stdout)
        value = float(info["format"]["duration"])
        if not info["streams"] or not math.isfinite(value) or value <= 0:
            raise ValueError("Expected audio with a positive finite duration")
        return round(value, 2)
    except FileNotFoundError:
        if required:
            raise ValueError("unavailable: Freesound import requires ffprobe on PATH") from None
    except (subprocess.SubprocessError, ValueError, KeyError, TypeError) as error:
        if required:
            raise ValueError(f"Invalid audio {path}: {error}") from error
    return None


class Library:
    def __init__(self, out):
        self.out = out
        path = out / "catalog.json"
        self.catalog = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        if not isinstance(self.catalog, list):
            raise ValueError("Existing catalog must be a JSON list")
        self.by_id, self.by_path, self.pending = {}, {}, []
        for row in self.catalog:
            if not isinstance(row, dict) or not row.get("id") or not row.get("path"):
                raise ValueError("Existing catalog contains an entry without ID/path")
            local_path(out, row["path"])
            if row["id"] in self.by_id or row["path"] in self.by_path:
                raise ValueError("Existing catalog has duplicate IDs/paths")
            self.by_id[row["id"]] = row
            self.by_path[row["path"]] = row
        self.existing_ids = set(self.by_id)

    def add(self, src, rel, kind, source, license_, note="", metadata=None):
        asset_id = rel.rsplit(".", 1)[0].replace("/", ".")
        existing = self.by_id.get(asset_id) or self.by_path.get(rel)
        dst = local_path(self.out, rel)
        if existing:
            if existing["id"] != asset_id or existing["path"] != rel:
                raise ValueError(f"Catalog ID/path conflict: {asset_id}")
            if metadata:
                # Different project versions must never replace the same sound.
                checksum = metadata["sha256"]
                if (existing.get("sha256") != checksum or
                        (asset_id in self.existing_ids and (not dst.is_file() or digest(dst) != checksum))):
                    raise ValueError(f"Freesound content conflict: {asset_id}")
            return
        if dst.exists() and digest(dst) != digest(src):
            raise ValueError(f"Refusing to overwrite an uncataloged/modified file: {dst}")
        row = {"id": asset_id, "path": rel, "kind": kind, "source": source,
               "license": license_, "duration": duration(src, required=metadata is not None), "note": note}
        if metadata:
            row.update(metadata)
        self.catalog.append(row)
        self.by_id[asset_id] = self.by_path[rel] = row
        self.pending.append((src, dst))

    def write(self):
        # All input validation precedes writes, including across manifests.
        for src, dst in self.pending:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
        self.out.mkdir(parents=True, exist_ok=True)
        target = self.out / "catalog.json"
        payload = json.dumps(self.catalog, ensure_ascii=False, indent=1)
        if target.exists() and target.read_text(encoding="utf-8") == payload:
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.out,
                                             delete=False) as handle:
                temporary = pathlib.Path(handle.name)
                handle.write(payload)
            temporary.replace(target)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def import_legacy(library, repos):
    hf = repos / "hyperframes/skills/media-use/audio/assets/sfx"
    manifest = {}
    if (hf / "manifest.json").exists():
        data = json.loads((hf / "manifest.json").read_text(encoding="utf-8"))
        for row in (data if isinstance(data, list) else data.get("sounds", data.get("files", []))):
            if isinstance(row, dict) and row.get("file"):
                manifest[row["file"]] = row
    for path in sorted(hf.glob("*.mp3")):
        note = json.dumps(manifest[path.name], ensure_ascii=False)[:200] if path.name in manifest else ""
        library.add(path, f"sfx/pixabay/{path.name}", "sfx", "hyperframes (Pixabay)", "Pixabay Content License", note)

    sc = repos / "video-shotcraft/assets/audio"
    attribution = sc / "ATTRIBUTION.md"
    # New upstream snapshots remove shared SFX; absence is not a deletion request.
    for line in attribution.read_text(encoding="utf-8").splitlines() if attribution.exists() else []:
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        url = next((url.rstrip(")>") for url in re.findall(r"https://[^\s|]+", " ".join(cells))
                    if (urlparse(url).hostname or "").endswith(".mixkit.co")
                    or urlparse(url).hostname == "mixkit.co"), None)
        if not url:
            continue
        name = cells[0]
        if name.endswith(".mp3"):
            folder = next((cell for cell in cells if cell.startswith("sfx/")), None)
            if folder:
                src = local_path(sc, f"{folder.rstrip('/')}/{name}")
                if src.is_file():
                    library.add(src, f"sfx/mixkit/{folder[4:].strip('/')}/{name}", "sfx",
                                "video-shotcraft (Mixkit)", "Mixkit Sound Effects Free License", url)
            else:
                src = local_path(sc, f"bgm/{name}")
                if src.is_file():
                    library.add(src, f"bgm/mixkit/{name}", "bgm", "video-shotcraft (Mixkit)",
                                "Mixkit Stock Music Free License", url)

    us = repos / "uisfx/packages/uisfx/sounds"
    if not us.exists():
        us = library.out / "sfx/uisfx"
    for path in sorted(us.glob("*/*.mp3")):
        library.add(path, f"sfx/uisfx/{path.parent.name}/{path.name}", "sfx", "uisfx", "CC0 1.0")


def license_code(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"creativecommons.org", "www.creativecommons.org"}:
        return None
    path = parsed.path.rstrip("/")
    if path == "/publicdomain/zero/1.0":
        return "CC0-1.0"
    match = re.fullmatch(r"/licenses/by/(1\.0|2\.0|2\.5|3\.0|4\.0)", path)
    return f"CC-BY-{match[1]}" if match else None


def import_freesound(library, manifest_path, policy):
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("assets"), list):
        raise ValueError(f"Expected a video-shotcraft v1 audio manifest: {manifest_path}")
    for row in data["assets"]:
        if not isinstance(row, dict):
            raise ValueError("Freesound asset must be an object")
        for key in ("id", "file", "provider", "title", "author", "page_url", "license", "license_url", "sha256"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Missing Freesound {key} in {manifest_path}")
        match = re.fullmatch(r"fs:([1-9][0-9]*)", row["id"])
        if not match or row["provider"] != "freesound":
            raise ValueError(f"Invalid Freesound provider/ID: {row['id']}")
        sid = match[1]
        page = urlparse(row["page_url"])
        if (page.scheme not in {"http", "https"} or page.hostname != "freesound.org"
                or not re.fullmatch(rf"/(?:people/[^/]+/sounds|s)/{sid}/?", page.path)):
            raise ValueError(f"Invalid Freesound page URL: {row['id']}")
        code = license_code(row["license_url"])
        if code != row["license"] or not code or (code != "CC0-1.0" and policy != "by"):
            raise ValueError(f"Unsupported/mismatched license for {row['id']}; CC BY requires --freesound-license by")
        src = local_path(manifest_path.parent, row["file"])
        if src.suffix.lower() not in {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".aiff", ".opus"}:
            raise ValueError(f"Unsupported audio extension: {src.name}")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or digest(src) != row["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {row['id']}")
        metadata = {"original_id": row["id"], "sha256": row["sha256"],
                    "title": row["title"], "author": row["author"], "page_url": row["page_url"],
                    "license_url": row["license_url"], "provenance": row}
        library.add(src, f"sfx/freesound/fs-{sid}{src.suffix.lower()}", "sfx",
                    "video-shotcraft (Freesound)", code, row["page_url"], metadata)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", default="_repos")
    parser.add_argument("--out", default="kit/audio-library")
    parser.add_argument("--manifest", "--freesound-manifest", action="append", default=[], type=pathlib.Path,
                        help="Project video-shotcraft v1 audio-manifest.json (repeatable; no network)")
    parser.add_argument("--freesound-license", choices=("cc0", "by"), default="cc0",
                        help="by also permits CC BY; retain its credits when publishing")
    args = parser.parse_args(argv)
    try:
        library = Library(pathlib.Path(args.out))
        import_legacy(library, pathlib.Path(args.repos))
        for manifest in args.manifest:
            import_freesound(library, manifest, args.freesound_license)
        library.write()
        counts = {}
        for row in library.catalog:
            counts[row["source"]] = counts.get(row["source"], 0) + 1
        print("tổng", len(library.catalog), counts)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"build_library: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    sys.exit(main())
