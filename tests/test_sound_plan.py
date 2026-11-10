"""Unit tests for tools/sound_plan.py (HyperFrames media-use sound plan)."""
import json
import pathlib
import pytest
import shutil

from tools.sound_plan import (
    infer_bgm_brief,
    estimate_word_timing_per_char,
    resolve_reveal_timing,
    plan_accents,
    build_sound_plan,
)


def test_infer_bgm_brief_archetypes(tmp_path):
    # 1. SaaS / tech default
    clip_dir = tmp_path / "clip_default"
    clip_dir.mkdir()
    (clip_dir / "clip.json").write_text(json.dumps({"title": "SaaS Platform Demo", "genre": "saas"}), encoding="utf-8")
    brief_default = infer_bgm_brief(clip_dir)
    assert brief_default["archetype"] == "saas-tech-default"
    assert brief_default["bpm"] == 108
    assert brief_default["brightness"] >= 0.7
    assert "instrumental, no vocals" in brief_default["prompt"]
    assert "MAJOR scale" in brief_default["prompt"]

    # 2. Demo loop
    clip_loop = tmp_path / "clip_loop"
    clip_loop.mkdir()
    (clip_loop / "clip.json").write_text(json.dumps({"title": "Loop Hook Screendemo", "genre": "demo"}), encoding="utf-8")
    (clip_loop / "BRIEF.md").write_text("Video nối vòng loop hook", encoding="utf-8")
    brief_loop = infer_bgm_brief(clip_loop)
    assert brief_loop["archetype"] == "demo-loop"
    assert brief_loop["bpm"] == 100  # 108 - 8
    assert brief_loop["is_loop"] is True
    assert "seamless loop" in brief_loop["prompt"]

    # 3. PAS / problem -> solution
    clip_pas = tmp_path / "clip_pas"
    clip_pas.mkdir()
    (clip_pas / "clip.json").write_text(json.dumps({"title": "Tại sao mình chưa xuất được?", "genre": "pas"}), encoding="utf-8")
    brief_pas = infer_bgm_brief(clip_pas)
    assert brief_pas["archetype"] == "problem-solution"
    assert brief_pas["scale"] == "MINOR to MAJOR build"
    assert "MINOR to MAJOR" in brief_pas["prompt"]

    # 4. Feature cascade
    clip_cascade = tmp_path / "clip_cascade"
    clip_cascade.mkdir()
    (clip_cascade / "clip.json").write_text(json.dumps({"title": "Tổng hợp tính năng mới", "genre": "feature"}), encoding="utf-8")
    brief_cascade = infer_bgm_brief(clip_cascade)
    assert brief_cascade["archetype"] == "feature-cascade"
    assert brief_cascade["bpm"] == 118  # 108 + 10


def test_estimate_word_timing_per_char():
    # Câu 50 ký tự, từ ở vị trí 25 -> thời gian khoảng giữa speech
    text = "Hai mươi tư tấn tiêu Việt Nam, đi từ Vũng Tàu sang Chicago."
    word = "Vũng Tàu"
    t = estimate_word_timing_per_char(
        line_text=text,
        target_word=word,
        speech_start=0.2,
        speech_end=4.2,
        piece_timeline_onset=10.0,
        piece_file_start=0.0,
    )
    # Vũng Tàu nằm ở khoảng giữa câu (offset ~37/58), t phải nằm trong khoảng (11.5, 13.5)
    assert 11.0 < t < 13.5


def test_resolve_reveal_timing():
    pieces = [
        {"line": "V2", "t": 7.0, "a": 0.0, "b": 3.0, "s": 0.2, "e": 2.8},
    ]
    voice_lines = [
        {"id": "V2", "text": "Câu trả lời nằm trong dữ liệu toàn cầu. StradeVn đọc nó cho bạn."},
    ]

    # Explicit time
    t, src, _ = resolve_reveal_timing(12.34, pieces, voice_lines)
    assert t == 12.34
    assert src == "explicit"

    # Tuple with line and word
    t, src, label = resolve_reveal_timing(("V2", "StradeVn"), pieces, voice_lines)
    assert t > 7.0
    assert src == "estimated_per_char"
    assert "V2:StradeVn" in label


def test_plan_accents_riser_and_hit():
    reveals = [
        {"line": "V2", "word": "StradeVn", "hit": "impact", "riser": "riser"},
    ]
    pieces = [
        {"line": "V2", "t": 15.0, "a": 0.0, "b": 4.0, "s": 0.1, "e": 3.9},
    ]
    voice_lines = [
        {"id": "V2", "text": "Câu trả lời là StradeVn giải pháp xuất khẩu."},
    ]
    memes = []
    existing_sfx = []

    planned_sfx, resolved_reveals = plan_accents(
        reveals=reveals,
        pieces=pieces,
        voice_lines=voice_lines,
        memes=memes,
        existing_sfx=existing_sfx,
        clip_duration=60.0,
    )

    # Must contain riser and hit
    hit = next((s for s in planned_sfx if s.get("kind") == "hit"), None)
    riser = next((s for s in planned_sfx if s.get("kind") == "riser"), None)

    assert hit is not None
    assert riser is not None
    assert hit["volume"] == 0.35
    assert riser["volume"] == 0.35

    # Riser ends exactly on reveal
    reveal_t = resolved_reveals[0]["time"]
    assert hit["t"] == reveal_t
    riser_end = riser["t"] + riser["dur"]
    assert abs(riser_end - reveal_t) < 0.01


def test_plan_accents_collision_with_meme():
    # Reveal nằm ngay trong thời gian meme diễn ra
    reveals = [{"time": 10.0, "hit": "impact", "riser": False}]
    memes = [{"t": 9.8, "dur": 1.5, "id": "meme1"}]
    pieces = []
    voice_lines = []

    planned_sfx, _ = plan_accents(
        reveals=reveals,
        pieces=pieces,
        voice_lines=voice_lines,
        memes=memes,
        existing_sfx=[],
    )
    # Bị loại do va chạm meme (< 0.6s)
    assert len(planned_sfx) == 0


def test_plan_accents_density_cap():
    # Hai reveal quá gần nhau (< 3.8s)
    reveals = [
        {"time": 10.0, "hit": "impact", "riser": False},
        {"time": 12.0, "hit": "impact", "riser": False},  # < 4s từ reveal trước
    ]
    planned_sfx, _ = plan_accents(
        reveals=reveals,
        pieces=[],
        voice_lines=[],
        memes=[],
        existing_sfx=[],
    )
    # Reveal thứ 2 bị loại do vượt trần mật độ
    hits = [s for s in planned_sfx if s.get("kind") == "hit"]
    assert len(hits) == 1
    assert hits[0]["t"] == 10.0


def test_build_sound_plan_schema(tmp_path):
    clip_dir = tmp_path / "clip_test"
    clip_dir.mkdir()
    (clip_dir / "clip.json").write_text(json.dumps({"title": "Test Clip", "genre": "saas"}), encoding="utf-8")
    (clip_dir / "voice.json").write_text(json.dumps({"lines": [{"id": "V1", "text": "StradeVn đọc nó cho bạn."}]}), encoding="utf-8")

    plan = build_sound_plan(
        clip_dir=clip_dir,
        reveals=[{"line": "V1", "word": "StradeVn", "hit": "impact", "riser": False}],
        pieces=[{"line": "V1", "t": 5.0, "a": 0.0, "b": 2.5, "s": 0.1, "e": 2.4}],
        target_duration=30.0,
    )

    assert plan["version"] == 1
    assert "bgm" in plan
    assert plan["bgm"]["volume"] == 0.12
    assert plan["bgm"]["duck_multiplier"] == 0.35
    assert plan["bgm"]["voice_carve"]["enabled"] is True
    assert plan["mixing"]["target_lufs"] == -14.0
    assert plan["mixing"]["max_true_peak_dbtp"] == -1.0


def test_find_library_file_concrete_names():
    from tools.sound_plan import _find_library_file, search_sfx_catalog

    # 1. Direct and slugified matches in audio-library
    f_sparkle = _find_library_file("sparkle")
    assert f_sparkle is not None
    assert "sparkle" in f_sparkle.name

    f_chime = _find_library_file("chime")
    assert f_chime is not None

    f_camera = _find_library_file("camera shutter")
    assert f_camera is not None
    assert "camera" in str(f_camera).lower()

    # 2. Search catalog/web.json with concrete names
    res = search_sfx_catalog("camera shutter", n=5)
    assert isinstance(res, list)
    if res:
        assert any("camera" in r.get("title", "").lower() or "shutter" in r.get("title", "").lower() for r in res)
