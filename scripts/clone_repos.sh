#!/usr/bin/env bash
# Optional research references audited 2026-11-09; never install/run upstream code.
# These are NOT audio asset pins. tools/fetch_sources.py owns legacy audio pins.
# Usage: bash scripts/clone_repos.sh CACHE_DIR [OWNER/REPO ...]
# Example: bash scripts/clone_repos.sh D:/agent-cache/references arhamhi/hooksmith
# No selection = all references. Historical 404s are unavailable, not successes.
# Exit 0: available refs verified; 1: repo failures; 2: usage/prerequisites.
# No speech/capture engines, packages, API keys or global Git changes needed.
set -u
set -o pipefail

usage() {
    printf 'Usage: bash %s CACHE_DIR [OWNER/REPO ...]\n' "$0"
    printf 'CACHE_DIR must be outside the kit. Names are OWNER--REPO.\n'
}
if [[ ${1:-} == --help || ${1:-} == -h ]]; then usage; exit 0; fi
if [[ $# -eq 0 || -z $1 || $1 == -* ]]; then usage >&2; exit 2; fi
for dependency in git realpath; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        printf 'UNAVAILABLE: %s is required; install it or use the bundled kit assets.\n' "$dependency" >&2
        exit 2
    fi
done

# Normalize D:/..., /d/... and relative paths in Git Bash, resolving symlinks.
canonical_path() {
    local path=$1
    if command -v cygpath >/dev/null 2>&1; then
        path=$(cygpath -u -- "$path") || return 1
    fi
    realpath -m -- "$path"
}
kit_root=$(canonical_path "$(dirname -- "${BASH_SOURCE[0]}")/..") || exit 2
cache_root=$(canonical_path "$1") || exit 2
shift
outside_kit() {
    [[ ${1,,} != "${kit_root,,}" && ${1,,} != "${kit_root,,}/"* ]]
}
if ! outside_kit "$cache_root"; then
    printf 'FAILED: cache must be outside the kit (including kit _repos/): %s\n' "$cache_root" >&2
    exit 2
fi

# Full immutable research pins from docs/research/repo-refresh-2026-11-09.md.
# Historical abbreviations are provenance, NOT checkout targets. Their complete
# SHAs are unknown; do not invent suffixes or try to refresh unavailable sources.
manifest=$(cat <<'PINS'
heygen-com/hyperframes c38ac5438c751094a720c55c68bd15fc6450ec37
Vincentwei1021/video-shotcraft 1266a3ec4831289c4d893d42dd5102723658039a
899ms/uisfx historical:9950fe6
arhamhi/hooksmith 1a1c13c313fe7c314233fccb2aa6bd2e8564373e
sharon-laicc/viral-video-decomposer 34093598d48bda6492f687c5eae3472b782d0637
shixinzhang/tiktok-viral-hooks c730c55d6d4a1fe01f91964a4651311910004042
jakeolschewski/short-form-video-scripts historical:f4f83d2
hypit-ai/hypit 2d31e88765e297f0795348b460c77a6067f12261
calesthio/OpenMontage fecb9a1e3cc23ef84de30b272059457a427f16f8
zhuyansen/awesome-claude-video-skills 6dbd11c4609a8bf2c536fd924d8bdb143d90f14d
wilwaldon/Claude-Code-Video-Toolkit a6e9e5225d85585472666598297f47d9584f9a97
kapishdima/soundcn 7cbfbb3f56e8548b81fb26410bdcea657447d087
openfilm/openfilm a85a80a9742981f0f77f61df88a2780984f8f3fb
louiseliu/hyperFrames-video-shotcraft 1df77f1ab080323558f70a5fb880fad0f88f87fc
kurbaitaev/ghost-editor ce172726c36293722b08eb57b5b307d4f06389e8
remotion-dev/skills 1af7e69a2a613437d46095924057970a6a7df40d
m-bain/whisperX 5d3678b8535698a2826a5db9eb3e4105aef85dd9
pnnbao97/VieNeu-TTS 6cdb62e03e6a9fd6ebff70e77aff8570c50949c3
CapSoftware/Cap a42f8f44f61c02b50302d755c41a7b739947a3e7
getopenscreen/openscreen 565ac5dc31c6bc56694eecb0502bad0cfcef4690
streamlink/streamlink ae15e79ea7e650bf2e715190d14b941f157e7112
iankiku/anytranscript 934d30fa52c7efadeed04a66db0858680c3f9876
digitalsamba/claude-code-video-toolkit f3d83c664554569c7e3411b614e5dda9eba350f9
heygen-com/hyperframes-community-skills ba7a0bb6d3567d124c51f6074625043bfe0b32eb
kmilo93sd/agent-video-editor 8e32c0aff64c445ef1e2b87bc04408a34d68c973
kyutai-labs/pocket-tts 28770c06f7deb1b65617834e60a6add7a4ff5b6d
latent-spaces/brag 669ab9286aa28b6c3ee30e75f181ee74319d012a
lonthq/overtone-captions 9fad13e25d59869ebed41f5979120f09b95abea0
langchain-ai/design-agent a6e15774409094adaa22654255bdcd8165cfb4ef
PINS
)

# Validate selections before creating directories or doing network work.
for requested in "$@"; do
    found=false
    while read -r repo pin; do
        if [[ $requested == "$repo" ]]; then found=true; break; fi
    done <<< "$manifest"
    if [[ $found == false ]]; then
        printf 'FAILED: unknown reference: %s (use exact OWNER/REPO).\n' "$requested" >&2
        exit 2
    fi
done

export GIT_TERMINAL_PROMPT=0
export GCM_INTERACTIVE=Never
git_at() {
    local directory=$1
    shift
    git -c "safe.directory=$directory" -c core.longpaths=true \
        -c http.sslBackend=openssl -c advice.detachedHead=false \
        -C "$directory" "$@"
}
failure_reason=''
fail_repo() {
    failure_reason=$1
    printf 'FAILED %s: %s\n' "$repo" "$failure_reason" >&2
    return 1
}
sync_repo() {
    local repo=$1 pin=$2 destination url root origin changes resolved head
    destination=$(canonical_path "$cache_root/${repo/\//--}") || { fail_repo 'cannot resolve cache path'; return 1; }
    if ! outside_kit "$destination"; then
        fail_repo 'cache entry resolves inside the kit'; return 1
    fi
    url="https://github.com/$repo.git"
    if [[ -e $destination ]]; then
        if [[ ! -d $destination/.git || -L $destination/.git ]]; then
            fail_repo "not a dedicated clone: $destination"; return 1
        fi
    else
        # init + exact SHA fetch avoids downloading a moving default branch.
        mkdir -p -- "$destination" || { fail_repo 'cannot create cache entry'; return 1; }
        git_at "$destination" init --quiet || { fail_repo 'init failed'; return 1; }
        git_at "$destination" remote add origin "$url" || { fail_repo 'remote setup failed'; return 1; }
    fi
    root=$(git_at "$destination" rev-parse --show-toplevel) || { fail_repo 'cannot identify working tree'; return 1; }
    root=$(canonical_path "$root") || { fail_repo 'cannot resolve working tree'; return 1; }
    if [[ ${root,,} != "${destination,,}" ]]; then
        fail_repo 'cache entry is not its own working tree'; return 1
    fi
    origin=$(git_at "$destination" config --get remote.origin.url) || { fail_repo 'origin unavailable'; return 1; }
    if [[ ${origin%.git} != "${url%.git}" ]]; then
        fail_repo "unexpected origin: $origin"; return 1
    fi
    changes=$(git_at "$destination" status --porcelain --untracked-files=all) || { fail_repo 'status check failed'; return 1; }
    if [[ -n $changes ]]; then
        fail_repo 'local changes present; use a clean dedicated cache'; return 1
    fi
    printf 'FETCH %s %s\n' "$repo" "$pin"
    git_at "$destination" fetch --quiet --no-tags --depth=1 origin "$pin" || { fail_repo 'fetch failed'; return 1; }
    resolved=$(git_at "$destination" rev-parse --verify "$pin^{commit}") || { fail_repo 'pin unavailable'; return 1; }
    if [[ $resolved != "$pin" ]]; then
        fail_repo "pin mismatch: $resolved"; return 1
    fi
    git_at "$destination" switch --quiet --detach "$pin" || { fail_repo 'switch to pin failed'; return 1; }
    head=$(git_at "$destination" rev-parse --verify HEAD) || { fail_repo 'HEAD verification failed'; return 1; }
    if [[ $head != "$pin" ]]; then
        fail_repo "HEAD mismatch: $head"; return 1
    fi
    printf 'OK %s %s %s\n' "$repo" "$head" "$destination"
}

successes=0
unavailable=0
failures=()
while read -r repo pin; do
    if [[ $# -gt 0 ]]; then
        selected=false
        for requested in "$@"; do
            if [[ $requested == "$repo" ]]; then selected=true; break; fi
        done
        if [[ $selected == false ]]; then continue; fi
    fi
    if [[ $pin == historical:* ]]; then
        printf 'UNAVAILABLE %s: public 404 at 2026-11-09 audit; historical %s (not refreshed).\n' "$repo" "${pin#historical:}"
        unavailable=$((unavailable + 1))
    elif [[ ! $pin =~ ^[0-9a-f]{40}$ ]]; then
        printf 'FAILED %s: invalid immutable pin: %s\n' "$repo" "$pin" >&2
        failures+=("$repo: invalid immutable pin")
    elif sync_repo "$repo" "$pin"; then
        successes=$((successes + 1))
    else
        failures+=("$repo: $failure_reason")
    fi
done <<< "$manifest"

printf 'SUMMARY: ok=%d failed=%d unavailable=%d\n' "$successes" "${#failures[@]}" "$unavailable"
if [[ ${#failures[@]} -gt 0 ]]; then
    printf 'Failure summary:\n' >&2
    printf '  %s\n' "${failures[@]}" >&2
    exit 1
fi
