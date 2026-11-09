"""Refresh pinned audio sources, then rebuild the library only after all succeed.

The kit already includes its audio library; this is an optional maintenance tool.
Research snapshots are references, never automatic asset upgrades. In particular,
video-shotcraft stays at legacy 5ddbf52 until the importer migration is approved.

Usage: python tools/fetch_sources.py [--repos ../_repos] [--out audio-library]
       python tools/fetch_sources.py --repos D:/agent-cache/sources --fetch-only

SRC-CATALOG handoff: keep build_library.py --repos/--out. New per-project and
AUDIO-CC0 manifests belong to explicit additive importer inputs, not this fetcher.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

KIT = Path(__file__).resolve().parent.parent

# Audited default-branch HEADs on 2026-11-09; deliberately NOT checkout targets.
RESEARCH_HEADS = {
    "hyperframes": "c38ac5438c751094a720c55c68bd15fc6450ec37",
    "video-shotcraft": "1266a3ec4831289c4d893d42dd5102723658039a",
}

# name, URL, immutable asset pin, sparse audio directory. Preserve importer names.
SOURCES = [
    ("hyperframes", "https://github.com/heygen-com/hyperframes.git",
     "9a27b9f9349b43b9fd194a95ace830d7cbe38b42", "skills/media-use/audio/assets/sfx"),
    ("video-shotcraft", "https://github.com/Vincentwei1021/video-shotcraft.git",
     "5ddbf521038b0a7accfb6dc1e0a9eb29c67277ab", "assets/audio"),
]
# uisfx is publicly unavailable: keep the kit's 936-file snapshot and importer
# fallback; do not attempt a mandatory clone or claim it was refreshed.


def git(directory, *args):
    """Run checked Git operations without changing global Git configuration."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", "-C", str(directory), "-c", "core.longpaths=true",
         "-c", "advice.detachedHead=false", *args],
        check=True, capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env,
    ).stdout.strip()


def fetch_source(repos, source):
    name, url, asset_pin, folder = source
    directory = repos / name
    print(f"Fetching {name}: asset pin {asset_pin}", flush=True)
    if not directory.exists():
        # init + fetch avoids a partial clone being mistaken for a ready cache.
        directory.mkdir()
        git(directory, "init", "-q")
        git(directory, "remote", "add", "origin", url)
        git(directory, "config", "remote.origin.promisor", "true")
        git(directory, "config", "remote.origin.partialclonefilter", "blob:none")
    elif not (directory / ".git").is_dir():
        raise ValueError(f"Not a dedicated Git clone: {directory}")

    # Never operate on the owner kit or a nested directory inside another repo.
    root = Path(git(directory, "rev-parse", "--show-toplevel")).resolve()
    if root != directory.resolve() or root == KIT.resolve():
        raise ValueError(f"Refusing to change this working tree: {directory}")
    if git(directory, "remote", "get-url", "origin").removesuffix(".git").lower() != url.removesuffix(".git").lower():
        raise ValueError(f"Unexpected origin for {name}; use a dedicated --repos cache")
    if git(directory, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"Source clone has local changes: {directory}")

    # A stale local object is not a successful refresh: fetch MUST succeed.
    git(directory, "fetch", "-q", "--filter=blob:none", "--depth=1", "origin", asset_pin)
    resolved = git(directory, "rev-parse", "--verify", f"{asset_pin}^{{commit}}")
    if resolved != asset_pin:
        raise ValueError(f"Asset pin mismatch for {name}: {resolved}")
    git(directory, "sparse-checkout", "set", "--no-cone", folder)
    git(directory, "checkout", "-q", "--detach", resolved)
    head = git(directory, "rev-parse", "--verify", "HEAD")
    if head != resolved:
        raise ValueError(f"Checkout mismatch for {name}: {head} != {resolved}")
    if not (directory / folder).is_dir():
        raise ValueError(f"Missing pinned audio directory: {directory / folder}")
    print(f"OK {name}: resolved asset SHA {head}; "
          f"research snapshot {RESEARCH_HEADS.get(name, 'unrecorded')} (reference only)", flush=True)
    return head


def rebuild_library(repos, out):
    """Build a copy first; a failed importer cannot overwrite audio/catalog."""
    out.parent.mkdir(parents=True, exist_ok=True)
    # Same-volume renames also work on Windows. Keep the original until success.
    with tempfile.TemporaryDirectory(prefix=".audio-refresh-", dir=out.parent) as temp:
        stage = Path(temp) / "library"
        backup = Path(temp) / "previous"
        if out.exists():
            shutil.copytree(out, stage)
        else:
            stage.mkdir()
        subprocess.run(
            [sys.executable, str(KIT / "tools" / "build_library.py"),
             "--repos", str(repos), "--out", str(stage)], check=True,
        )
        if not (stage / "catalog.json").is_file():
            raise ValueError("Importer did not produce catalog.json; library not published")
        had_library = out.exists()
        if had_library:
            out.rename(backup)
        try:
            stage.rename(out)
        except OSError:
            if had_library:
                backup.rename(out)
            raise
    print(f"OK library published: {out}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repos", type=Path, default=KIT.parent / "_repos",
                        help="dedicated source cache (legacy default: beside kit)")
    parser.add_argument("--out", type=Path, default=KIT / "audio-library",
                        help="library destination; existing files seed the staged rebuild")
    parser.add_argument("--fetch-only", action="store_true",
                        help="verify pinned sources without invoking the importer")
    args = parser.parse_args(argv)
    try:
        if shutil.which("git") is None:
            raise ValueError("git unavailable; install Git or use the bundled audio-library")
        repos, out = args.repos.resolve(), args.out.resolve()
        if repos == KIT.resolve() or KIT.resolve() in repos.parents:
            raise ValueError("--repos must be outside the kit working tree")
        if out == KIT.resolve() or out in KIT.resolve().parents:
            raise ValueError("--out must not replace the kit or its parent directories")
        if out == repos or repos in out.parents or out in repos.parents:
            raise ValueError("--out and --repos must be separate, non-nested directories")
        repos.mkdir(parents=True, exist_ok=True)
        for source in SOURCES:
            fetch_source(repos, source)
        if not args.fetch_only:
            rebuild_library(repos, out)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        detail = (exc.stderr or "").strip() if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(f"ERROR: refresh failed; library was not replaced: {detail or exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    sys.exit(main())
