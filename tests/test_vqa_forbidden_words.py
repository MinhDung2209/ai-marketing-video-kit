"""Unit tests for forbidden phrases and badge emojis."""
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

from tools.vqa.checks.brief.forbidden_phrases import check_forbidden_phrases
from tools.vqa.context import VQAContext


@pytest.fixture
def fake_clip_dir(tmp_path):
    clip = tmp_path / "test_clip"
    clip.mkdir()
    return clip


def test_forbidden_to_khai_in_voice_text(fake_clip_dir):
    voice_data = {
        "lines": [
            {
                "id": "V1",
                "text": "Xem chi tiết trên tờ khai hải quan của lô hàng.",
                "caption": "Xem chi tiết lô hàng.",
            }
        ]
    }
    (fake_clip_dir / "voice.json").write_text(json.dumps(voice_data, ensure_ascii=False), encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_forbidden_phrases(ctx)
    assert len(issues) >= 1
    assert any("tờ khai" in iss.msg for iss in issues)


def test_forbidden_third_party_brand(fake_clip_dir):
    voice_data = {
        "lines": [
            {
                "id": "V2",
                "text": "Dữ liệu đối thủ lấy từ panjiva và importgenius cập nhật mỗi ngày.",
                "caption": "Dữ liệu cập nhật mỗi ngày.",
            }
        ]
    }
    (fake_clip_dir / "voice.json").write_text(json.dumps(voice_data, ensure_ascii=False), encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_forbidden_phrases(ctx)
    assert len(issues) >= 2
    assert any("panjiva" in iss.msg for iss in issues)
    assert any("importgenius" in iss.msg for iss in issues)


def test_emoji_in_badge_flagged(fake_clip_dir):
    voice_data = {"lines": []}
    (fake_clip_dir / "voice.json").write_text(json.dumps(voice_data), encoding="utf-8")

    html = '<section><div class="step">24 TẤN 🇻🇳 → 🇺🇸 AI MUA?</div></section>'
    (fake_clip_dir / "index.html").write_text(html, encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_forbidden_phrases(ctx)
    assert len(issues) >= 1
    assert any("emoji" in iss.msg for iss in issues)


def test_clean_badges_pass(fake_clip_dir):
    voice_data = {
        "lines": [
            {
                "id": "V1",
                "text": "Dữ liệu xuất nhập khẩu toàn cầu cho doanh nghiệp.",
                "caption": "Dữ liệu xuất nhập khẩu toàn cầu.",
            }
        ]
    }
    (fake_clip_dir / "voice.json").write_text(json.dumps(voice_data, ensure_ascii=False), encoding="utf-8")

    html = '<section><div class="step">24 TẤN · VŨNG TÀU → CHICAGO · AI MUA?</div></section>'
    (fake_clip_dir / "index.html").write_text(html, encoding="utf-8")

    ctx = VQAContext(fake_clip_dir)
    issues = check_forbidden_phrases(ctx)
    assert len(issues) == 0
