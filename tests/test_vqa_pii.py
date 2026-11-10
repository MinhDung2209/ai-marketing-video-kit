"""Unit tests for PII scanning."""
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

from tools.vqa.checks.shots.pii_scan import check_pii_scan
from tools.vqa.context import VQAContext


@pytest.fixture
def fake_clip_dir(tmp_path):
    clip = tmp_path / "test_clip"
    clip.mkdir()
    screen = clip / "assets" / "screen" / "s1"
    screen.mkdir(parents=True)
    return clip


def test_pii_scan_detects_owner_gmail(fake_clip_dir):
    s1_dir = fake_clip_dir / "assets" / "screen" / "s1"
    marks = [
        {
            "name": "login_step",
            "t": 1.2,
            "element_text": "Chào mừng stradevn@gmail.com quay trở lại",
        }
    ]
    (s1_dir / "marks.json").write_text(json.dumps({"marks": marks}), encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_pii_scan(ctx)
    assert len(issues) >= 1
    assert any("stradevn@gmail.com" in iss.msg for iss in issues)
    assert any("s1/login_step" in iss.where for iss in issues)


def test_pii_scan_allows_public_business_email(fake_clip_dir):
    s1_dir = fake_clip_dir / "assets" / "screen" / "s1"
    marks = [
        {
            "name": "contact_row",
            "t": 3.4,
            "element_text": "Email liên hệ: customerservice@stcharlestrading.com",
        }
    ]
    (s1_dir / "marks.json").write_text(json.dumps({"marks": marks}), encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_pii_scan(ctx)
    assert len(issues) == 0


def test_pii_scan_detects_private_phone_in_dom_snapshot(fake_clip_dir):
    s1_dir = fake_clip_dir / "assets" / "screen" / "s1"
    dom_dir = s1_dir / "_dom"
    dom_dir.mkdir()
    (dom_dir / "001_snap.txt").write_text("Hỗ trợ kỹ thuật: 0987654321", encoding="utf-8")
    marks = [
        {
            "name": "snap",
            "t": 2.0,
            "page_text_path": "_dom/001_snap.txt",
        }
    ]
    (s1_dir / "marks.json").write_text(json.dumps({"marks": marks}), encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_pii_scan(ctx)
    assert len(issues) >= 1
    assert any("0987654321" in iss.msg for iss in issues)
