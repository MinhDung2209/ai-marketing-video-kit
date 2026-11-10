"""Unit tests for VQA sfx_timing and bgm_entry checks."""
import json
import pytest
from pathlib import Path

from tools.vqa.context import VQAContext
from tools.vqa.checks.build.sfx_timing import check_sfx_timing
from tools.vqa.checks.build.bgm_entry import check_bgm_entry


def test_sfx_timing_valid(tmp_path):
    clip_dir = tmp_path / "valid_clip"
    clip_dir.mkdir()
    cues = {
        "duration": 60.0,
        "bgm": {"file": "bgm.mp3", "start": 0.0, "volume": 0.12, "loop": True},
        "sfx": [
            # Riser ends at 10.0 (t=0.0 + dur=10.0), hit at 10.0 -> valid
            {"t": 0.0, "dur": 10.0, "file": "sfx/pixabay/riser.mp3", "reveal_target": 10.0, "kind": "riser"},
            {"t": 10.0, "dur": 1.5, "file": "sfx/mixkit/impact/bass-hit-short.mp3", "reveal_target": 10.0, "kind": "hit"},
            # Next accent at 18.0s (> 4s and > 0.6s)
            {"t": 18.0, "dur": 1.0, "file": "sfx/mixkit/ui/ui-option-select.mp3"},
        ],
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_sfx_timing(ctx)
    assert len(issues) == 0


def test_sfx_timing_riser_mismatch(tmp_path):
    clip_dir = tmp_path / "mismatch_clip"
    clip_dir.mkdir()
    cues = {
        "duration": 60.0,
        "sfx": [
            # Riser ends at 9.0s (t=0, dur=9.0) but reveal is at 10.0s (diff 1.0s > 0.15s)
            {"t": 0.0, "dur": 9.0, "file": "sfx/pixabay/riser.mp3", "reveal_target": 10.0, "kind": "riser"},
            {"t": 10.0, "dur": 1.5, "file": "sfx/mixkit/impact/bass-hit-short.mp3", "reveal_target": 10.0, "kind": "hit"},
        ],
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_sfx_timing(ctx)
    assert any("Riser kết thúc lệch" in iss.msg for iss in issues)


def test_sfx_timing_accents_too_close(tmp_path):
    clip_dir = tmp_path / "close_accents"
    clip_dir.mkdir()
    cues = {
        "duration": 60.0,
        "sfx": [
            {"t": 10.0, "dur": 1.0, "file": "sfx/mixkit/impact/bass-hit-short.mp3", "kind": "hit"},
            {"t": 10.3, "dur": 1.0, "file": "sfx/pixabay/impact-bass-1.mp3", "kind": "hit"},  # 0.3s < 0.6s
        ],
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_sfx_timing(ctx)
    assert any("quá gần nhau" in iss.msg for iss in issues)


def test_sfx_timing_meme_collision(tmp_path):
    clip_dir = tmp_path / "meme_col"
    clip_dir.mkdir()
    cues = {
        "duration": 60.0,
        "sfx": [
            {"t": 5.0, "dur": 2.0, "file": "meme:vine-boom"},
            {"t": 5.2, "dur": 1.0, "file": "sfx/mixkit/impact/bass-hit-short.mp3", "kind": "hit"},  # đè meme
        ],
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_sfx_timing(ctx)
    assert any("nằm đè hoặc cách meme" in iss.msg for iss in issues)


def test_sfx_timing_density_cap_exceeded(tmp_path):
    clip_dir = tmp_path / "high_density"
    clip_dir.mkdir()
    # 20 giây mà có 10 accents (> 1 per 4s)
    cues = {
        "duration": 20.0,
        "sfx": [{"t": float(i * 1.5), "dur": 0.5, "file": "sfx/mixkit/impact/hit.mp3", "kind": "hit"} for i in range(10)],
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_sfx_timing(ctx)
    assert any("Mật độ accent SFX quá dày" in iss.msg for iss in issues)


def test_bgm_entry_valid(tmp_path):
    clip_dir = tmp_path / "valid_bgm"
    clip_dir.mkdir()
    cues = {
        "duration": 45.0,
        "bgm": {"file": "bgm.mp3", "start": 0.0, "offset": 0.0, "loop": True},
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_bgm_entry(ctx)
    assert len(issues) == 0


def test_bgm_entry_late_start(tmp_path):
    clip_dir = tmp_path / "late_bgm"
    clip_dir.mkdir()
    cues = {
        "duration": 45.0,
        "bgm": {"file": "bgm.mp3", "start": 1.2, "offset": 0.0, "loop": True},  # 1.2s > 0.5s
    }
    (clip_dir / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
    ctx = VQAContext(clip_dir)

    issues = check_bgm_entry(ctx)
    assert any("Nhạc nền vào muộn" in iss.msg for iss in issues)
