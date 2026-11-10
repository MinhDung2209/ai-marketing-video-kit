"""Tests cho screendemo/story_json.py và sự tương đương duration."""
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
sys.path.insert(0, str(ROOT / "screendemo"))

import story_json


def test_story_json_build_equivalence(tmp_path):
    c05_src = pathlib.Path("D:/agent-cache/ORCH/c05")
    if not (c05_src / "story.json").exists():
        pytest.skip("Fixture c05 không có sẵn tại D:/agent-cache/ORCH/c05")

    # Tạo copy trong tmp_path
    c05_copy = tmp_path / "c05_test"
    shutil.copytree(c05_src, c05_copy)

    # Chạy story_json.build
    dur = story_json.build(c05_copy, variant="full", emit_py=True)

    # Kiểm tra duration đạt 97.41s ±0.1s
    assert abs(dur - 97.41) <= 0.1, f"Duration {dur}s lệch quá ±0.1s so với mốc 97.41s"

    # Kiểm tra các file đầu ra sinh đủ
    assert (c05_copy / "index.html").exists()
    assert (c05_copy / "cues.json").exists()
    assert (c05_copy / "story.py").exists()

    # Kiểm tra cues.json có fade của video loop
    cues = json.loads((c05_copy / "cues.json").read_text(encoding="utf-8"))
    assert cues.get("duration") == round(dur, 2)
    assert cues.get("bgm", {}).get("fade_in") == 0.05
    assert cues.get("bgm", {}).get("fade_out") == 0.15
