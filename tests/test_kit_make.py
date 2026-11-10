"""Unit tests cho kit make: state, schemas, safety, gate retry, và story_json."""
import json
import os
import pathlib
import sys
import tempfile
import pytest
import shutil

_agent_tmp = pathlib.Path("D:/agent-cache/ORCH/tmp")
try:
    _agent_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(_agent_tmp)
    os.environ["TEMP"] = str(_agent_tmp)
    tempfile.tempdir = str(_agent_tmp)
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from make.state import RunState, ALL_STAGES
from make.schema import validate_data, load_schema
from make.safety import check_forbidden_steps
from make.gate import run_stage_with_gate_loop, format_gate_feedback
from make.llm import set_mock_handler, extract_json_from_text


# ---------------------------------------------------------------- Test 1: RunState & Resume
def test_run_state_lifecycle_and_resume(tmp_path):
    clip_dir = tmp_path / "test_clip"
    state = RunState(clip_dir)

    # Khởi tạo
    state.init_if_new(
        url="https://app.example.com",
        goal="Demo video",
        profile="stradevn",
        len_sec=60,
        loop=True,
        model="agy:gemini-3.8-flash-high",
    )
    assert (clip_dir / "run.json").exists()
    assert state.data["url"] == "https://app.example.com"
    assert state.data["loop"] is True

    # Cập nhật stage
    state.start_stage("discover")
    assert state.get_stage_status("discover") == "running"
    state.finish_stage("discover", {"facts_count": 10})
    assert state.is_done("discover")
    assert state.get_stage_status("discover") == "done"

    # Kiểm tra xác định stage cần chạy khi resume
    stages = state.determine_stages_to_run()
    assert stages[0] == "brief"  # vì discover đã done
    assert "discover" not in stages

    # Kiểm tra --from
    stages_from = state.determine_stages_to_run(from_stage="voice")
    assert stages_from[0] == "voice"
    assert "shots" not in stages_from

    # Kiểm tra --only
    stages_only = state.determine_stages_to_run(only_stage="story")
    assert stages_only == ["story"]

    # Kiểm tra fail stage
    state.start_stage("brief")
    state.fail_stage("brief", error="Gate QA rejected", retries=3)
    assert state.get_stage_status("brief") == "failed"


# ---------------------------------------------------------------- Test 2: Schemas Validation
def test_schemas_validation():
    # 1. Brief Schema
    valid_brief = {
        "profile": "stradevn",
        "goal": "Test goal",
        "chosen_hook": "A",
        "loop": True,
        "scenes": [
            {
                "id": "C1",
                "voice_line": {
                    "id": "V1",
                    "text": "Hai mươi tư tấn tiêu",
                    "direction": "Nhanh, dồn dập"
                },
                "badge": "24 TẤN TIÊU"
            }
        ],
        "facts_used": [
            {"key": "R_ROW", "value": "24000 KGS", "source": "inventory"}
        ]
    }
    ok, err = validate_data(valid_brief, "brief")
    assert ok, f"Valid brief failed: {err}"

    invalid_brief = {"goal": "Missing profile and scenes"}
    ok, err = validate_data(invalid_brief, "brief")
    assert not ok
    assert err is not None

    # 2. Voice Schema
    valid_voice = {
        "model": "gemini-3.1-flash-tts-preview",
        "voice": "Puck",
        "profile": "Sales mentor",
        "lines": [
            {"id": "V1", "text": "Lời thoại một", "direction": "Ấm áp"},
            {"id": "V2", "text": "Lời thoại hai", "direction": "Tự tin"}
        ]
    }
    ok, err = validate_data(valid_voice, "voice")
    assert ok, f"Valid voice failed: {err}"

    # Invalid voice: line id sai pattern
    invalid_voice = dict(valid_voice, lines=[{"id": "INVALID", "text": "...", "direction": "..."}])
    ok, err = validate_data(invalid_voice, "voice")
    assert not ok

    # 3. Shots Schema
    valid_shots = {
        "profile": "stradevn",
        "viewport": [1080, 1350],
        "shots": {
            "s1": {
                "note": "Hook",
                "steps": [
                    {"do": "goto", "url": "https://example.com"},
                    {"do": "wait", "sec": 1.0},
                    {"do": "mark", "name": "rong"}
                ]
            }
        }
    }
    ok, err = validate_data(valid_shots, "shots")
    assert ok, f"Valid shots failed: {err}"

    # 4. Sources Schema
    valid_sources = [
        {"id": "sfx-whoosh", "scene": "C1", "kind": "sfx", "query_en": "whoosh transition"},
        {"id": "bgm", "scene": "all", "kind": "bgm", "query_en": "tech beat"}
    ]
    ok, err = validate_data(valid_sources, "sources")
    assert ok, f"Valid sources failed: {err}"

    # 5. Story Schema
    valid_story = {
        "version": "1.0",
        "title": "Test Story",
        "bgm": {"file": "assets/src/bgm.mp3"},
        "scenes": [
            {
                "id": "C1",
                "type": "screen",
                "rec": "s1",
                "r0": "rong",
                "r1": "het",
                "badge": "TIÊU ĐỀ",
                "items": [
                    {"line": "V1", "i": 0, "j": 2, "at": "rong"}
                ]
            }
        ]
    }
    ok, err = validate_data(valid_story, "story")
    assert ok, f"Valid story failed: {err}"


# ---------------------------------------------------------------- Test 3: Safety Forbidden Steps
def test_safety_check_forbidden_steps():
    clean_shots = {
        "shots": {
            "s1": {
                "steps": [
                    {"do": "goto", "url": "https://example.com"},
                    {"do": "click", "target": {"text": "Xem chi tiết"}},
                    {"do": "wait", "sec": 1.0}
                ]
            }
        }
    }
    ok, errors = check_forbidden_steps(clean_shots)
    assert ok
    assert len(errors) == 0

    forbidden_shots = {
        "shots": {
            "s1": {
                "steps": [
                    {"do": "click", "target": {"text": "Tạo chiến dịch"}},
                    {"do": "click", "target": {"has_text": "Bắt đầu truy xuất"}},
                    {"do": "click", "target": "button:has-text('Gửi ngay')"}
                ]
            }
        }
    }
    ok, errors = check_forbidden_steps(forbidden_shots)
    assert not ok
    assert len(errors) == 3
    assert any("tạo chiến dịch" in e["msg"].lower() for e in errors)
    assert any("bắt đầu truy xuất" in e["msg"].lower() for e in errors)
    assert any("gửi ngay" in e["msg"].lower() for e in errors)


# ---------------------------------------------------------------- Test 4: Gate Retry Loop with Fake LLM
def test_gate_retry_loop_success():
    attempt_count = 0
    received_feedbacks = []

    def fake_llm(feedback):
        nonlocal attempt_count
        attempt_count += 1
        received_feedbacks.append(feedback)
        return {"attempt": attempt_count}

    def fake_gate():
        if attempt_count < 3:
            return {
                "ok": False,
                "errors": [
                    {
                        "check": "missing_badge",
                        "where": "C1",
                        "msg": "Cảnh 1 thiếu badge tiêu đề",
                        "fix_hint": "Bổ sung trường badge vào cảnh C1"
                    }
                ]
            }
        return {"ok": True, "errors": []}

    res = run_stage_with_gate_loop("test_stage", fake_llm, fake_gate, max_retries=3)
    assert res == {"attempt": 3}
    assert attempt_count == 3
    assert received_feedbacks[0] is None
    assert "missing_badge" in received_feedbacks[1]
    assert "Bổ sung trường badge" in received_feedbacks[1]


def test_gate_retry_loop_exceeded_raises():
    def fake_llm(feedback):
        return {}

    def always_fail_gate():
        return {
            "ok": False,
            "errors": [{"check": "fatal_err", "where": "shots", "msg": "Cannot resolve"}]
        }

    with pytest.raises(RuntimeError) as exc_info:
        run_stage_with_gate_loop("fail_stage", fake_llm, always_fail_gate, max_retries=2)
    assert "dừng lại sau 2 lần thử không qua được Gate" in str(exc_info.value)


# ---------------------------------------------------------------- Test 5: JSON Extraction from text
def test_extract_json_from_text():
    raw_str = 'Some thought here.\n```json\n{"ok": true, "count": 42}\n```\nMore text.'
    data = extract_json_from_text(raw_str)
    assert data == {"ok": True, "count": 42}

    raw_no_fence = 'Prefix text {"name": "test", "num": 123} suffix'
    data2 = extract_json_from_text(raw_no_fence)
    assert data2 == {"name": "test", "num": 123}
