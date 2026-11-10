"""Unit tests for Vietnamese number word parser and normalizer."""
from __future__ import annotations

import pytest

from tools.vqa.number_parser import (
    check_presence_in_dom,
    extract_numbers_from_voice_text,
    normalize_numeric_string,
    parse_compound_vietnamese_number,
)


def test_vietnamese_compound_integers():
    assert parse_compound_vietnamese_number(["hai", "mươi", "tư"]) == 24.0
    assert parse_compound_vietnamese_number(["mười", "chín"]) == 19.0
    assert parse_compound_vietnamese_number(["mười", "tám"]) == 18.0
    assert parse_compound_vietnamese_number(["mười", "hai"]) == 12.0
    assert parse_compound_vietnamese_number(["hai", "mươi"]) == 20.0
    assert parse_compound_vietnamese_number(["hai", "mươi", "tư", "nghìn"]) == 24000.0
    assert parse_compound_vietnamese_number(["một", "trăm", "linh", "năm"]) == 105.0


def test_vietnamese_decimal_numbers():
    assert parse_compound_vietnamese_number(["sáu", "phẩy", "sáu", "tư"]) == 6.64
    assert parse_compound_vietnamese_number(["ba", "phẩy", "bốn", "lăm"]) == 3.45
    assert parse_compound_vietnamese_number(["mười", "bảy", "phẩy", "tám"]) == 17.8


def test_normalize_numeric_strings():
    assert normalize_numeric_string("24.000") == 24000.0
    assert normalize_numeric_string("24,000") == 24000.0
    assert normalize_numeric_string("24000") == 24000.0
    assert normalize_numeric_string("$6,64") == 6.64
    assert normalize_numeric_string("6.64") == 6.64
    assert normalize_numeric_string("6,64 / KG") == 6.64
    assert normalize_numeric_string("17,680") == 17680.0
    assert normalize_numeric_string("37.128 USD") == 37128.0
    assert normalize_numeric_string("$9,635,200") == 9635200.0


def test_extract_numbers_from_voice_text():
    # V1: 24 tấn
    v1 = "Hai mươi tư tấn tiêu Việt Nam, đi từ Vũng Tàu sang Chicago."
    nums = extract_numbers_from_voice_text(v1)
    assert any(n["val"] == 24.0 for n in nums)

    # V3: HS code sequence 0904.11
    v3 = "Không cần nhớ mã HS. Gõ hồ tiêu, ra ngay không chín không bốn, mười một."
    nums3 = extract_numbers_from_voice_text(v3)
    assert any("0904.11" in n.get("equivalents", []) for n in nums3)

    # V6: 18 nhà cung cấp, $6.64
    v6 = "Tab Đối thủ: mười tám nhà cung cấp, sáu phẩy sáu tư đô một ký"
    nums6 = extract_numbers_from_voice_text(v6)
    assert any(n["val"] == 18.0 for n in nums6)
    assert any(abs(n["val"] - 6.64) < 0.001 for n in nums6)


def test_check_presence_in_dom():
    # 24 tấn spoken vs 24000 KGS in DOM
    nums = extract_numbers_from_voice_text("hai mươi tư tấn tiêu")[0]
    assert check_presence_in_dom(nums, "Dòng dữ liệu: 24000 KGS - Vũng Tàu sang Chicago")
    assert check_presence_in_dom(nums, "Dòng dữ liệu: 24.000 KGS")
    assert check_presence_in_dom(nums, "Dòng dữ liệu: 24 tấn")

    # sáu phẩy sáu tư đô vs $6,64 / KG in DOM
    num_price = extract_numbers_from_voice_text("sáu phẩy sáu tư đô một ký")[0]
    assert check_presence_in_dom(num_price, "Đơn giá: $6,64 / KG")
    assert check_presence_in_dom(num_price, "Giá trung bình: 6.64 USD")

    # proper noun in DOM
    assert check_presence_in_dom("Chicago", "Cảng dỡ hàng: CHICAGO US")
    assert check_presence_in_dom("Harris Spice", "Công ty: HARRIS SPICE ASIA PACIFIC")
    assert not check_presence_in_dom("Tokyo", "Cảng dỡ hàng: CHICAGO US")
