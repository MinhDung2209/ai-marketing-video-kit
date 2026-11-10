"""Unit tests for loop seam pixel difference calculation."""
from __future__ import annotations

import io
from PIL import Image
import pytest

from tools.vqa.checks.build.loop_seam import compute_frame_difference


def make_png_bytes(color: tuple, size=(100, 100)) -> bytes:
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_identical_frames_have_zero_diff():
    b1 = make_png_bytes((120, 150, 200))
    b2 = make_png_bytes((120, 150, 200))
    diff = compute_frame_difference(b1, b2)
    assert diff == 0.0


def test_slightly_different_frames():
    b1 = make_png_bytes((100, 100, 100))
    b2 = make_png_bytes((105, 105, 105))
    diff = compute_frame_difference(b1, b2)
    assert 4.9 < diff < 5.1


def test_completely_different_frames():
    b1 = make_png_bytes((0, 0, 0))
    b2 = make_png_bytes((255, 255, 255))
    diff = compute_frame_difference(b1, b2)
    assert diff == 255.0
