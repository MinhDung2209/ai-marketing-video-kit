"""Hệ thống kế hoạch âm thanh chuyên nghiệp (Sound Plan) cho video demo sản phẩm.
Chuẩn hoá BGM narrative archetype, Best Entry analysis, Beat-aligned Accent SFX (risers & hits),
và HyperFrames-compliant mixing graph (ducking, voice-band carve, -14 LUFS, True Peak < -1 dBTP).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

KIT = pathlib.Path(__file__).resolve().parent.parent
LIB = KIT / "audio-library"
SFX_DIR = LIB / "sfx"


def _probe_duration(f: str | pathlib.Path) -> Optional[float]:
    """Lấy thời lượng thật (giây) của file âm thanh qua ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def _find_library_file(name_or_rel: str, clip_dir: Optional[pathlib.Path] = None) -> Optional[pathlib.Path]:
    """Tìm file SFX/BGM theo tên cụ thể trong clip assets hoặc audio-library."""
    if not name_or_rel:
        return None
    p = pathlib.Path(name_or_rel)
    if p.is_absolute() and p.exists():
        return p

    norm = name_or_rel.strip().lower()
    slug = norm.replace(" ", "-").replace("_", "-")

    candidates = []
    if clip_dir:
        candidates.extend([
            clip_dir / name_or_rel,
            clip_dir / "assets" / "src" / name_or_rel,
            clip_dir / "assets" / "src" / f"sfx-{slug}.mp3",
            clip_dir / "assets" / "src" / f"{slug}.mp3",
            clip_dir / "assets" / "src" / f"sfx-{norm}.mp3",
            clip_dir / "assets" / "src" / f"{norm}.mp3",
        ])

    candidates.extend([
        LIB / name_or_rel,
        LIB / slug,
        SFX_DIR / "pixabay" / f"{slug}.mp3",
        SFX_DIR / "pixabay" / f"{norm}.mp3",
        SFX_DIR / "pixabay" / slug,
        SFX_DIR / "mixkit" / "impact" / f"{slug}.mp3",
        SFX_DIR / "mixkit" / "impact" / slug,
        SFX_DIR / "mixkit" / "ui" / f"{slug}.mp3",
        SFX_DIR / "mixkit" / "ui" / slug,
        SFX_DIR / "uisfx" / f"{slug}.mp3",
        LIB / "bgm" / "mixkit" / f"{slug}.mp3",
        LIB / "bgm" / "lyria" / f"{slug}.wav",
    ])

    for c in candidates:
        if c.exists():
            return c

    # Search recursively in SFX_DIR for exact stem or slug match
    if SFX_DIR.exists():
        for f in SFX_DIR.rglob("*.mp3"):
            stem = f.stem.lower()
            if stem == slug or stem == f"sfx-{slug}":
                return f
        for f in SFX_DIR.rglob("*.mp3"):
            stem = f.stem.lower()
            if slug in stem:
                return f

    return None


def search_sfx_catalog(query: str, max_dur: float = 6.0, n: int = 10) -> List[Dict[str, Any]]:
    """Tìm kiếm SFX theo tên cụ thể (e.g. 'camera shutter', 'cash register') từ catalog.json và web.json."""
    try:
        from tools import audio_web
        return audio_web.catalog(query, "sfx", max_dur, None, n)
    except Exception:
        return []


def _is_accent_sfx(file_name: str, label: str = "") -> bool:
    """Xác định xem một SFX có phải là accent (hit, impact, riser, chime, sparkle, bell, pop) không."""
    fn = (file_name or "").lower()
    lbl = (label or "").lower()
    if any(k in fn for k in ("typing", "click", "mouse")):
        return False
    return any(k in fn or k in lbl for k in ("riser", "impact", "hit", "chime", "sparkle", "bell", "pop", "accent"))


# ---------------------------------------------------------------------------
# 1(a). BGM brief by narrative archetype & Lyria prompt
# ---------------------------------------------------------------------------
def infer_bgm_brief(clip_dir: pathlib.Path | str, explicit_arc: Optional[str] = None) -> Dict[str, Any]:
    """Sinh brief BGM và prompt Lyria theo narrative archetype của video.

    HyperFrames narrative archetypes:
      - PAS (problem -> solution): MINOR to MAJOR build
      - feature cascade: +10 BPM driving
      - demo/loop: -8 BPM minimal, subtle groove, seamless loop
      - SaaS / tech default: uplifting corporate tech, bright modern piano with synth pads, ~108 BPM
      - Promo: brightness >= 0.7
    """
    clip_path = pathlib.Path(clip_dir).resolve()
    clip_json = {}
    p_json = clip_path / "clip.json"
    if p_json.exists():
        try:
            clip_json = json.loads(p_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    brief_text = ""
    p_brief = clip_path / "BRIEF.md"
    if p_brief.exists():
        try:
            brief_text = p_brief.read_text(encoding="utf-8").lower()
        except Exception:
            pass

    genre = (clip_json.get("genre") or "").lower()
    title = (clip_json.get("title") or "").lower()
    profile = (clip_json.get("profile") or "").lower()
    all_text = f"{genre} {title} {profile} {brief_text} {explicit_arc or ''}".lower()

    # Base genre detection
    if any(k in all_text for k in ("crypto", "nft", "web3", "defi", "blockchain")):
        base_desc = "atmospheric electronic, deep bass, futuristic synths, restrained percussion"
        base_bpm = 100
    elif any(k in all_text for k in ("finance", "fintech", "bank", "invest", "wealth", "tiền tệ")):
        base_desc = "calm cinematic, soft strings, subtle piano, restrained percussion"
        base_bpm = 92
    elif any(k in all_text for k in ("creative", "agency", "design", "studio", "art")):
        base_desc = "playful electronic, warm pads, light percussion"
        base_bpm = 115
    else:  # SaaS / tech / platform default
        base_desc = "uplifting corporate tech, bright modern piano with synth pads"
        base_bpm = 108

    # Archetype detection & modifiers
    is_loop = "loop" in all_text or "nối vòng" in all_text or "vòng" in all_text
    is_feature_cascade = "feature" in all_text or "tính năng" in all_text or "cascade" in all_text
    is_pas = "pas" in all_text or "problem" in all_text or "vấn đề" in all_text or "sao mình chưa" in all_text

    archetype = "saas-tech-default"
    bpm = base_bpm
    scale = "MAJOR"
    density = 0.55
    brightness = 0.75  # Promo brightness >= 0.7
    modifiers = []

    if is_loop:
        archetype = "demo-loop"
        bpm = base_bpm - 8
        density = 0.48
        modifiers.append("minimal subtle groove, seamless loop structure, clean steady pulse")
    elif is_feature_cascade:
        archetype = "feature-cascade"
        bpm = base_bpm + 10
        density = 0.65
        modifiers.append("driving momentum, rhythmic forward motion")
    elif is_pas:
        archetype = "problem-solution"
        scale = "MINOR to MAJOR build"
        density = 0.60
        modifiers.append("tension to relief progression, minor intro transitioning into confident major resolution")

    # Combine into Lyria prompt
    parts = [base_desc]
    if modifiers:
        parts.extend(modifiers)
    parts.append(f"{scale} scale")
    parts.append(f"{bpm} BPM")
    parts.append("instrumental, no vocals")

    prompt = ", ".join(parts)
    negative_prompt = "vocals, singing, speech, heavy distortion, harsh noise, muddy mix"

    return {
        "archetype": archetype,
        "base_bpm": base_bpm,
        "bpm": bpm,
        "brightness": brightness,
        "density": density,
        "scale": scale,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "is_loop": is_loop,
    }


# ---------------------------------------------------------------------------
# 1(b). Best Entry analysis (5s windows, ebur128/onset energy)
# ---------------------------------------------------------------------------
def analyze_best_entry(
    track_path: pathlib.Path | str,
    target_duration: float,
    is_loop: bool = False,
    window_size: float = 5.0,
    max_scan: float = 30.0,
) -> Dict[str, Any]:
    """Phân tích các cửa sổ 5s của bài nhạc bằng ffmpeg ebur128/energy để tìm điểm vào sạch và chắc nhất.

    Cắt từ điểm đó, áp fade-in ngắn và fade-out dài hơn; đảm bảo phủ hết video không đuôi lặng.
    Với video nối vòng (loop clips): fade-in/fade-out rất ngắn để liền mạch (seamless).
    """
    track = pathlib.Path(track_path).resolve()
    if not track.exists():
        return {
            "best_offset": 0.0,
            "fade_in": 0.05 if is_loop else 0.5,
            "fade_out": 0.15 if is_loop else 2.5,
            "reason": "track not found on disk, default 0.0s",
        }

    total_dur = _probe_duration(track) or 60.0
    # Scan candidate windows: 0, 5, 10, 15...
    candidates = []
    t = 0.0
    limit = min(max_scan, max(0.0, total_dur - 6.0))
    while t <= limit:
        candidates.append(round(t, 2))
        t += window_size

    scores = []
    for cand in candidates:
        try:
            cmd = [
                "ffmpeg", "-nostdin", "-hide_banner", "-nostats",
                "-ss", str(cand), "-t", str(window_size),
                "-i", str(track),
                "-af", "ebur128=peak=true",
                "-f", "null", "-",
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            out = r.stderr
            # Parse Integrated loudness and Peak
            i_match = re.findall(r"I:\s+(-?[\d.]+)\s+LUFS", out)
            p_match = re.findall(r"Peak:\s+(-?[\d.]+)\s+dBFS", out)
            i_val = float(i_match[-1]) if i_match else -70.0
            p_val = float(p_match[-1]) if p_match else -70.0

            # Measure first 0.5s of the candidate window to verify clean onset vs silence
            cmd_lead = [
                "ffmpeg", "-nostdin", "-hide_banner", "-nostats",
                "-ss", str(cand), "-t", "0.5",
                "-i", str(track),
                "-af", "astats=metadata=1:reset=1",
                "-f", "null", "-",
            ]
            r_lead = subprocess.run(cmd_lead, capture_output=True, text=True, timeout=10)
            rms_match = re.findall(r"RMS level dB:\s+(-?[\d.]+)", r_lead.stderr)
            lead_rms = float(rms_match[-1]) if rms_match else -70.0

            # Clean entrance score: active energy (not silent) and solid onset
            # Avoid quiet intros (< -28 LUFS) when a later section has a full drop
            score = i_val + (10.0 if lead_rms > -35.0 else -15.0)
            scores.append((cand, i_val, p_val, lead_rms, score))
        except Exception:
            scores.append((cand, -70.0, -70.0, -70.0, -100.0))

    best_offset = 0.0
    reason = "opening entrance is clear and energetic"

    if scores:
        cand0 = scores[0]
        # If t=0 has very low energy (e.g. quiet build < -26 LUFS) and another window is significantly stronger
        other_bests = [s for s in scores[1:] if s[1] > cand0[1] + 4.0 and s[3] > -30.0]
        if cand0[1] < -25.0 and other_bests:
            top_cand = max(other_bests, key=lambda s: s[4])
            # Check if trimming from top_cand still covers cut or looping is active
            if is_loop or (total_dur - top_cand[0] >= target_duration - 1.0):
                best_offset = top_cand[0]
                reason = f"trimmed from quiet intro ({cand0[1]:.1f} LUFS) to strong entrance at {best_offset:.1f}s ({top_cand[1]:.1f} LUFS)"

    # Fades per HyperFrames
    if is_loop:
        fade_in = 0.05
        fade_out = 0.15
    else:
        fade_in = 0.5
        fade_out = 2.2

    return {
        "best_offset": best_offset,
        "fade_in": fade_in,
        "fade_out": fade_out,
        "scores": scores,
        "reason": reason,
        "is_loop": is_loop,
        "total_duration": total_dur,
    }


# ---------------------------------------------------------------------------
# 1(c). Accent SFX from beat structure (word timing, riser, hit, collisions)
# ---------------------------------------------------------------------------
def estimate_word_timing_per_char(
    line_text: str,
    target_word: str,
    speech_start: float,
    speech_end: float,
    piece_timeline_onset: float,
    piece_file_start: float,
) -> float:
    """Ước lượng thời điểm nói 1 từ theo tỉ lệ ký tự trong câu khi chưa có alignment chi tiết."""
    clean = re.sub(r"\[[^\]]*\]", " ", line_text).strip()
    idx = clean.lower().find(target_word.lower())
    if idx < 0:
        # If exact word not found, place in middle of the line
        ratio = 0.5
    else:
        # Center of the word
        word_center = idx + len(target_word) / 2.0
        ratio = max(0.0, min(1.0, word_center / max(1, len(clean))))

    dur = max(0.0, speech_end - speech_start)
    char_time_in_file = speech_start + ratio * dur
    word_timeline_time = piece_timeline_onset + (char_time_in_file - piece_file_start)
    return round(word_timeline_time, 3)


def resolve_reveal_timing(
    reveal_def: Any,
    pieces: List[Dict[str, Any]],
    voice_lines: List[Dict[str, Any]],
    timing_data: Optional[Dict[str, Any]] = None,
) -> Tuple[float, str, str]:
    """Trả về (timeline_seconds, timing_source, label)."""
    # 1. Explicit float/int timestamp
    if isinstance(reveal_def, (int, float)):
        return round(float(reveal_def), 3), "explicit", f"t={reveal_def:.2f}s"

    # 2. Tuple ("V2", "StradeVn")
    line_id = None
    target_word = None
    explicit_t = None
    if isinstance(reveal_def, (list, tuple)) and len(reveal_def) >= 2:
        line_id = str(reveal_def[0])
        target_word = str(reveal_def[1])
    elif isinstance(reveal_def, dict):
        if "time" in reveal_def:
            explicit_t = float(reveal_def["time"])
        line_id = reveal_def.get("line")
        target_word = reveal_def.get("word")

    if explicit_t is not None:
        return round(explicit_t, 3), "explicit", f"t={explicit_t:.2f}s"

    if not line_id:
        return 0.0, "default", "start"

    # Find matching piece from story
    matching_pieces = [p for p in pieces if p.get("line") == line_id]
    piece = matching_pieces[0] if matching_pieces else None

    # Check for word alignment in timing_data if available
    if timing_data and target_word:
        lines = timing_data.get("lines", [])
        for l in lines:
            if l.get("id") == line_id and "words" in l:
                for w in l["words"]:
                    if target_word.lower() in w.get("text", "").lower():
                        w_start = float(w["start"])
                        if piece:
                            t = piece["t"] + (w_start - piece["a"])
                        else:
                            t = float(l.get("start", 0)) + w_start
                        return round(t, 3), "aligned", f"{line_id}:{target_word}"

    # Estimate per-character
    vl = next((l for l in voice_lines if l.get("id") == line_id), None)
    text = (vl.get("text") if vl else "") or target_word or ""
    if piece:
        t = estimate_word_timing_per_char(
            line_text=text,
            target_word=target_word or "",
            speech_start=piece.get("s", piece["a"]),
            speech_end=piece.get("e", piece["b"]),
            piece_timeline_onset=piece["t"],
            piece_file_start=piece["a"],
        )
        print(f"  [sound_plan] reveal {line_id}:{target_word!r} ước lượng per-char @ {t:.2f}s")
        return t, "estimated_per_char", f"{line_id}:{target_word}"

    return 0.0, "fallback", f"{line_id}:{target_word}"


def plan_accents(
    reveals: List[Any],
    pieces: List[Dict[str, Any]],
    voice_lines: List[Dict[str, Any]],
    memes: List[Dict[str, Any]],
    existing_sfx: List[Dict[str, Any]],
    clip_dir: Optional[pathlib.Path] = None,
    clip_duration: float = 60.0,
    timing_data: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Tạo danh sách accent SFX (riser + hit) với kiểm tra va chạm, kết thúc đúng lúc, và trần mật độ.

    Rules:
      - Riser ENDS exactly on reveal: start = reveal - riser_len (real duration via ffprobe).
      - Hit/impact exactly on reveal word.
      - NO accent where a meme or another accent is within 0.6 s.
      - Density cap: <= 1 accent per ~4 s.
      - SFX named concretely: 'riser', 'impact', 'chime', 'sparkle', 'cash register', etc.
    """
    resolved_reveals = []
    for r in reveals:
        t, src, label = resolve_reveal_timing(r, pieces, voice_lines, timing_data)
        r_dict = r if isinstance(r, dict) else {}
        hit_name = r_dict.get("hit", "impact") if r_dict.get("hit") is not False else None
        riser_name = r_dict.get("riser", "riser") if r_dict.get("riser") is not False else None

        # Custom explicit names or True
        if hit_name is True:
            hit_name = "impact"
        if riser_name is True:
            riser_name = "riser"

        resolved_reveals.append({
            "time": t,
            "source": src,
            "label": label,
            "hit": hit_name,
            "riser": riser_name,
            "raw": r,
        })

    # Sort reveals by time
    resolved_reveals.sort(key=lambda x: x["time"])

    # Locate concrete sound files
    riser_file = _find_library_file("riser", clip_dir) or _find_library_file("sfx-riser", clip_dir)
    impact_file = _find_library_file("impact", clip_dir) or _find_library_file("sfx-impact", clip_dir) or _find_library_file("bass-hit-short", clip_dir)

    riser_dur = _probe_duration(riser_file) if riser_file else 10.03
    if not riser_dur:
        riser_dur = 10.03

    # Collect meme zones (start, end)
    meme_zones = []
    for m in memes:
        mt = float(m.get("t", 0))
        mdur = float(m.get("dur", 2.0))
        meme_zones.append((mt - 0.6, mt + mdur + 0.6))

    # Existing scene whooshes or manual sfx
    scene_whoosh_times = [float(s.get("t", 0)) for s in existing_sfx if "whoosh" in str(s.get("file", "")).lower()]
    existing_accent_times = [
        float(s.get("t", 0)) for s in existing_sfx
        if _is_accent_sfx(str(s.get("file", "")), str(s.get("label", "")))
    ]

    planned_sfx: List[Dict[str, Any]] = []
    planned_accent_times: List[float] = []

    for rev in resolved_reveals:
        rev_t = rev["time"]

        # Check collision with existing accents (< 0.6s)
        if any(abs(rev_t - eat) < 0.6 for eat in existing_accent_times):
            print(f"  [sound_plan] bỏ qua reveal @ {rev_t:.2f}s: trùng accent có sẵn (< 0.6s)")
            continue

        # Check meme collision for reveal point
        in_meme = any(z0 <= rev_t <= z1 for z0, z1 in meme_zones)
        if in_meme:
            print(f"  [sound_plan] bỏ qua reveal @ {rev_t:.2f}s: trùng vùng meme")
            continue

        # Check density cap: <= 1 accent cluster per 4.0s
        if planned_accent_times and (rev_t - planned_accent_times[-1]) < 3.8:
            print(f"  [sound_plan] bỏ qua reveal @ {rev_t:.2f}s: vượt trần mật độ (<= 1 accent / 4s)")
            continue

        # 1. Riser: ends exactly on reveal
        if rev.get("riser") and riser_file:
            r_start = rev_t - riser_dur
            # If riser starts before 0, trim so it ends on reveal_t
            if r_start < 0:
                trimmed_start = round(abs(r_start), 3)
                riser_cue = {
                    "t": 0.0,
                    "file": str(riser_file),
                    "volume": 0.35,
                    "dur": round(rev_t, 3),
                    "offset": trimmed_start,
                    "label": f"riser -> {rev['label']}",
                    "reveal_target": rev_t,
                    "kind": "riser",
                }
            else:
                riser_cue = {
                    "t": round(r_start, 3),
                    "file": str(riser_file),
                    "volume": 0.35,
                    "dur": round(riser_dur, 3),
                    "label": f"riser -> {rev['label']}",
                    "reveal_target": rev_t,
                    "kind": "riser",
                }

            # Check if riser span collides with meme
            riser_col = any(max(riser_cue["t"], z0) <= min(rev_t, z1) for z0, z1 in meme_zones)
            if not riser_col:
                planned_sfx.append(riser_cue)

        # 2. Hit: exactly on reveal
        if rev.get("hit"):
            hit_file = _find_library_file(str(rev["hit"]), clip_dir) or impact_file
            if hit_file:
                # Ensure no duplicate scene whoosh at same exact second
                hit_cue = {
                    "t": round(rev_t, 3),
                    "file": str(hit_file),
                    "volume": 0.35,
                    "label": f"hit on {rev['label']}",
                    "reveal_target": rev_t,
                    "kind": "hit",
                }
                planned_sfx.append(hit_cue)
                planned_accent_times.append(rev_t)

    return planned_sfx, resolved_reveals


# ---------------------------------------------------------------------------
# 1(d). Mixing configuration & export
# ---------------------------------------------------------------------------
def build_sound_plan(
    clip_dir: pathlib.Path | str,
    reveals: Optional[List[Any]] = None,
    pieces: Optional[List[Dict[str, Any]]] = None,
    memes: Optional[List[Dict[str, Any]]] = None,
    existing_sfx: Optional[List[Dict[str, Any]]] = None,
    bgm_file: Optional[str] = None,
    target_duration: float = 60.0,
) -> Dict[str, Any]:
    """Tạo toàn bộ sound_plan.json hoàn chỉnh cho clip."""
    clip_path = pathlib.Path(clip_dir).resolve()

    # Load voice lines
    voice_lines = []
    p_voice = clip_path / "voice.json"
    if p_voice.exists():
        try:
            vdoc = json.loads(p_voice.read_text(encoding="utf-8"))
            voice_lines = vdoc.get("lines", [])
        except Exception:
            pass

    # Load timing data if present
    timing_data = None
    p_timing = clip_path / "audio" / "timing.json"
    if p_timing.exists():
        try:
            timing_data = json.loads(p_timing.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 1. BGM brief & prompt
    bgm_brief = infer_bgm_brief(clip_path)

    # 2. Best entry
    resolved_bgm = _find_library_file(bgm_file or "bgm/mixkit/house-vibez.mp3", clip_path)
    entry_plan = analyze_best_entry(
        track_path=resolved_bgm or "",
        target_duration=target_duration,
        is_loop=bgm_brief.get("is_loop", False),
    )

    # 3. Accents
    pieces = pieces or []
    memes = memes or []
    existing_sfx = existing_sfx or []

    # If reveals omitted, infer automatic reveals
    if reveals is None:
        reveals = []
        # Find hook reveal, question answer, or brand mentions
        for p in pieces:
            lid = p.get("line", "")
            vl = next((l for l in voice_lines if l.get("id") == lid), None)
            text = (vl.get("text") or "").lower()
            if "stradevn" in text:
                reveals.append({"line": lid, "word": "StradeVn", "hit": "impact", "riser": True})
            elif "đáp án" in text or "harris" in text:
                reveals.append({"line": lid, "word": "Harris", "hit": "chime", "riser": False})
            elif "ai mua" in text:
                reveals.append({"line": lid, "word": "ai mua", "hit": "impact", "riser": False})

    accents, resolved_reveals = plan_accents(
        reveals=reveals,
        pieces=pieces,
        voice_lines=voice_lines,
        memes=memes,
        existing_sfx=existing_sfx,
        clip_dir=clip_path,
        clip_duration=target_duration,
        timing_data=timing_data,
    )

    plan = {
        "version": 1,
        "clip": clip_path.name,
        "duration": target_duration,
        "archetype": bgm_brief["archetype"],
        "bgm": {
            "brief": bgm_brief,
            "file": str(resolved_bgm.relative_to(clip_path).as_posix()) if resolved_bgm and resolved_bgm.is_relative_to(clip_path) else str(resolved_bgm or bgm_file),
            "volume": 0.12,  # HyperFrames bed volume under voice
            "duck_multiplier": 0.35,  # HyperFrames 0.3-0.4
            "entry": entry_plan,
            "voice_carve": {
                "enabled": True,
                "frequency": 2500,
                "width_hz": 2000,
                "gain_db": -4.0,
            },
        },
        "reveals": resolved_reveals,
        "accents": accents,
        "mixing": {
            "sfx_bus_volume": 0.35,
            "bgm_volume": 0.12,
            "duck_multiplier": 0.35,
            "target_lufs": -14.0,
            "max_true_peak_dbtp": -1.0,
            "carve_eq": "equalizer=f=2500:t=h:w=2000:g=-4",
        },
    }

    return plan


def apply_sound_plan_to_story(st: Any, reveals: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Hook được gọi từ engine.Story: tính toán sound plan và áp dụng trực tiếp vào st."""
    clip_dir = st.proj
    target_dur = float(st.state.get("now", 60.0))

    # Collect memes from stickers or existing sfx
    memes = []
    for s in st.stickers:
        memes.append({"t": s["t"], "dur": s["dur"], "id": s.get("id")})

    plan = build_sound_plan(
        clip_dir=clip_dir,
        reveals=reveals,
        pieces=st.pieces,
        memes=memes,
        existing_sfx=st.sfx,
        bgm_file=getattr(st, "_bgm_file", None),
        target_duration=target_dur,
    )

    # Add planned accents to st.sfx
    for acc in plan["accents"]:
        cue = dict(
            t=acc["t"],
            file=acc["file"],
            volume=acc.get("volume", 0.35),
        )
        if acc.get("dur"):
            cue["dur"] = acc["dur"]
        if acc.get("offset"):
            cue["offset"] = acc["offset"]
        st.sfx.append(cue)

    # Save sound_plan.json
    out_dir = st.out
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sound_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [sound_plan] đã áp dụng sound_plan.json ({len(plan['accents'])} accents, archetype={plan['archetype']})")

    st._sound_plan = plan
    return plan


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Tạo và kiểm tra sound_plan.json cho clip")
    ap.add_argument("clip", help="Thư mục clip")
    ap.add_argument("--reveals", help="JSON string danh sách reveals", default=None)
    ap.add_argument("--out", help="Đường dẫn file xuất sound_plan.json", default=None)
    a = ap.parse_args()

    clip_dir = pathlib.Path(a.clip).resolve()
    revs = json.loads(a.reveals) if a.reveals else None
    plan = build_sound_plan(clip_dir=clip_dir, reveals=revs)

    out_file = pathlib.Path(a.out) if a.out else (clip_dir / "sound_plan.json")
    out_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Đã ghi sound plan vào {out_file}")


if __name__ == "__main__":
    main()
