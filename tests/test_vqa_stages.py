"""Unit tests for VQA stage runner and remaining checks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

_agent_tmp = Path("D:/agent-cache/QA1/tmp")
try:
    _agent_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(_agent_tmp)
    os.environ["TEMP"] = str(_agent_tmp)
    tempfile.tempdir = str(_agent_tmp)
except Exception:
    pass

import pytest

from tools.vqa.checks.brief.line_ids import check_line_ids
from tools.vqa.checks.brief.number_words import check_number_words
from tools.vqa.checks.brief.profile_direction import check_profile_direction
from tools.vqa.checks.brief.required_phrases import check_required_phrases
from tools.vqa.checks.brief.speech_length import check_speech_length
from tools.vqa.checks.brief.loop import check_loop_hook
from tools.vqa.checks.shots.ink_marks import check_ink_marks
from tools.vqa.checks.shots.viewport import check_viewport
from tools.vqa.checks.build.duration import check_duration
from tools.vqa.checks.build.stickers import check_stickers
from tools.vqa.checks.build.sfx_exist import check_sfx_exist
from tools.vqa.context import VQAContext
from tools.vqa.runner import run_stage


@pytest.fixture
def fake_clip(tmp_path):
    clip = tmp_path / "c_test"
    clip.mkdir()
    return clip


def test_line_ids_validation(fake_clip):
    # Invalid ids
    v_data = {"lines": [{"id": "line1", "text": "hello"}]}
    (fake_clip / "voice.json").write_text(json.dumps(v_data), encoding="utf-8")
    ctx = VQAContext(fake_clip)
    issues = check_line_ids(ctx)
    assert len(issues) >= 1
    assert any("line1" in iss.msg for iss in issues)

    # Valid ids
    v_data2 = {"lines": [{"id": "V1", "text": "hello"}, {"id": "V2", "text": "world"}]}
    (fake_clip / "voice.json").write_text(json.dumps(v_data2), encoding="utf-8")
    ctx2 = VQAContext(fake_clip)
    assert len(check_line_ids(ctx2)) == 0


def test_number_words_validation(fake_clip):
    # Digits in voice text
    v_data = {"lines": [{"id": "V1", "text": "Có 24 tấn tiêu đi Mỹ."}]}
    (fake_clip / "voice.json").write_text(json.dumps(v_data), encoding="utf-8")
    ctx = VQAContext(fake_clip)
    issues = check_number_words(ctx)
    assert len(issues) >= 1
    assert any("24" in iss.msg for iss in issues)

    # Words in voice text
    v_data2 = {"lines": [{"id": "V1", "text": "Có hai mươi tư tấn tiêu đi Mỹ."}]}
    (fake_clip / "voice.json").write_text(json.dumps(v_data2), encoding="utf-8")
    ctx2 = VQAContext(fake_clip)
    assert len(check_number_words(ctx2)) == 0


def test_profile_direction_validation(fake_clip):
    # Short profile (<40 words) and identical direction
    v_data = {
        "profile": "Short profile only few words here.",
        "lines": [
            {"id": "V1", "direction": "same tone", "text": "one"},
            {"id": "V2", "direction": "same tone", "text": "two"},
        ]
    }
    (fake_clip / "voice.json").write_text(json.dumps(v_data), encoding="utf-8")
    ctx = VQAContext(fake_clip)
    issues = check_profile_direction(ctx)
    assert len(issues) >= 2
    assert any("ngắn" in iss.msg for iss in issues)
    assert any("sao chép" in iss.msg for iss in issues)


def test_ink_marks_limit(fake_clip):
    s_dir = fake_clip / "assets" / "screen" / "s1"
    s_dir.mkdir(parents=True)
    # 3 ink marks > max 2
    marks = [
        {"name": "m1", "t": 1.0, "box": {"x": 10, "y": 10, "w": 20, "h": 20}},
        {"name": "m2", "t": 2.0, "box": {"x": 10, "y": 10, "w": 20, "h": 20}},
        {"name": "m3", "t": 3.0, "box": {"x": 10, "y": 10, "w": 20, "h": 20}},
    ]
    (s_dir / "marks.json").write_text(json.dumps({"marks": marks}), encoding="utf-8")
    ctx = VQAContext(fake_clip)
    issues = check_ink_marks(ctx)
    assert len(issues) >= 1
    assert any("3 lần khoanh mực" in iss.msg for iss in issues)


def test_viewport_check(fake_clip):
    shots = {"viewport": [720, 1080]}
    (fake_clip / "shots.json").write_text(json.dumps(shots), encoding="utf-8")
    ctx = VQAContext(fake_clip)
    issues = check_viewport(ctx)
    assert len(issues) >= 1
    assert any("viewport" in iss.check for iss in issues)


def test_stickers_pacing(fake_clip):
    story_content = """
st.add_sticker("stk1", 1.5)
st.add_sticker("stk2", 5.0)
"""
    (fake_clip / "story.py").write_text(story_content, encoding="utf-8")
    ctx = VQAContext(fake_clip)
    issues = check_stickers(ctx)
    # One too early (< 3s), spacing too short (5.0 - 1.5 = 3.5s < 10s)
    assert len(issues) >= 2
