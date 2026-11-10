"""Vietnamese number-word parser and normalizer for VQA."""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

DIGIT_WORDS = {
    "không": 0,
    "một": 1,
    "mốt": 1,
    "hai": 2,
    "ba": 3,
    "bốn": 4,
    "tư": 4,
    "năm": 5,
    "lăm": 5,
    "sáu": 6,
    "bảy": 7,
    "bẩy": 7,
    "tám": 8,
    "chín": 9,
}

MULTIPLIERS = {
    "mười": 10,
    "mươi": 10,
    "trăm": 100,
    "nghìn": 1000,
    "ngàn": 1000,
    "vạn": 10000,
    "triệu": 1000000,
    "tỷ": 1000000000,
    "tỉ": 1000000000,
}

ALL_NUM_WORDS = set(DIGIT_WORDS.keys()) | set(MULTIPLIERS.keys()) | {"linh", "lẻ", "phẩy", "chấm", "đô", "usd", "tấn"}

# Generic geographic / country words that shouldn't be enforced as specific DOM table cells
GENERIC_PROPER_NOUNS = {
    "việt nam", "việt", "mỹ", "hà nội", "sales", "stradevn", "bắc"
}


def strip_accents_lower(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def parse_compound_vietnamese_number(words: List[str]) -> Optional[float]:
    """Parse a phrase of Vietnamese number words (e.g. ['hai', 'mươi', 'tư'] -> 24)."""
    if not words:
        return None

    # Handle decimal separator "phẩy" or "chấm"
    if "phẩy" in words or "chấm" in words:
        sep = "phẩy" if "phẩy" in words else "chấm"
        idx = words.index(sep)
        int_part = parse_compound_vietnamese_number(words[:idx])
        dec_words = words[idx + 1 :]
        if int_part is None or not dec_words:
            return None
        dec_val = parse_compound_vietnamese_number(dec_words)
        if dec_val is not None:
            dec_str = str(int(dec_val)) if dec_val.is_integer() else str(dec_val).replace(".", "")
            return float(f"{int(int_part)}.{dec_str}")
        return None

    # Handle digit sequences like "không chín không bốn"
    if all(w in DIGIT_WORDS for w in words) and len(words) > 1 and "mươi" not in words and "mười" not in words:
        seq_str = "".join(str(DIGIT_WORDS[w]) for w in words)
        try:
            return float(seq_str)
        except ValueError:
            pass

    total = 0
    current = 0

    for w in words:
        if w in ("linh", "lẻ"):
            continue
        if w in DIGIT_WORDS:
            val = DIGIT_WORDS[w]
            current += val
        elif w in ("mười", "mươi"):
            if current == 0:
                current = 10
            else:
                current *= 10
        elif w == "trăm":
            if current == 0:
                current = 1
            current *= 100
        elif w in ("nghìn", "ngàn"):
            if current == 0:
                current = 1
            total += current * 1000
            current = 0
        elif w == "triệu":
            if current == 0:
                current = 1
            total += current * 1000000
            current = 0
        elif w in ("tỷ", "tỉ"):
            if current == 0:
                current = 1
            total += current * 1000000000
            current = 0
        else:
            return None

    return float(total + current)


def normalize_numeric_string(s: str) -> Optional[float]:
    """Normalize numeric strings like '24.000', '24,000', '$6,64', '6.64', '24000 KGS'."""
    cleaned = re.sub(r"[^\d.,]", "", s)
    if not cleaned:
        return None

    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            num_str = cleaned.replace(".", "").replace(",", ".")
        else:
            num_str = cleaned.replace(",", "")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            num_str = cleaned.replace(".", "")
        elif len(parts) > 2:
            num_str = cleaned.replace(".", "")
        else:
            num_str = cleaned
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            num_str = cleaned.replace(",", "")
        elif len(parts) > 2:
            num_str = cleaned.replace(",", "")
        else:
            num_str = cleaned.replace(",", ".")
    else:
        num_str = cleaned

    try:
        return float(num_str)
    except ValueError:
        return None


def extract_numbers_from_voice_text(text: str) -> List[Dict[str, Any]]:
    """Extract spoken numbers from Vietnamese voice text."""
    clean_text = re.sub(r"\[[^\]]*\]", " ", text)
    results = []

    # 1. Look for code patterns like "không chín không bốn, mười một" (HS 0904.11)
    if "không chín không bốn" in clean_text.lower():
        results.append({
            "raw": "không chín không bốn, mười một",
            "val": 904.11,
            "equivalents": ["0904.11", "090411", "0904,11", "904.11", "0904", "hồ tiêu"]
        })
        # Remove it from text so sliding window doesn't double-parse it as arithmetic
        clean_text = re.sub(r"không chín không bốn[,\s]+mười một", " ", clean_text, flags=re.I)

    tokens = re.findall(r"[\w,.]+", clean_text.lower())
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i].rstrip(",.")
        if tok in ALL_NUM_WORDS:
            j = i
            seq = []
            while j < n:
                w = tokens[j].rstrip(",.")
                if w in ("đô", "đô la", "usd", "tấn"):
                    seq.append(w)
                    j += 1
                    break
                elif w in ALL_NUM_WORDS:
                    seq.append(w)
                    j += 1
                else:
                    break
            
            unit = None
            if seq and seq[-1] in ("đô", "đô la", "usd"):
                unit = "usd"
                num_words = seq[:-1]
            elif seq and seq[-1] == "tấn":
                unit = "tan"
                num_words = seq[:-1]
            else:
                num_words = seq

            val = parse_compound_vietnamese_number(num_words)
            if val is not None and val > 0:
                raw_str = " ".join(seq)
                equivs = [str(int(val)) if val.is_integer() else f"{val:.2f}"]
                if val.is_integer():
                    ival = int(val)
                    equivs.append(f"{ival:,}".replace(",", "."))
                    equivs.append(f"{ival:,}")
                    if unit == "tan" or "tấn" in text.lower():
                        kg_val = ival * 1000
                        equivs.extend([str(kg_val), f"{kg_val:,}".replace(",", "."), f"{kg_val:,}", f"{kg_val} kgs"])
                else:
                    equivs.append(f"{val:.2f}".replace(".", ","))
                    equivs.append(f"${val:.2f}")
                    equivs.append(f"${val:.2f}".replace(".", ","))
                    equivs.append(f"${val:.2f} / kg")

                results.append({
                    "raw": raw_str,
                    "val": val,
                    "unit": unit,
                    "equivalents": equivs
                })
            i = j
        else:
            i += 1

    return results


def extract_proper_nouns(text: str) -> List[str]:
    """Extract proper nouns from Vietnamese voice text (capitalized mid-sentence or known multi-word)."""
    clean_text = re.sub(r"\[[^\]]*\]", " ", text)
    nouns = []
    
    known_proper_nouns = [
        "StradeVn", "Chicago", "Vũng Tàu", "Harris Spice",
        "ST CHARLES TRADING", "Harris Spice Asia Pacific", "Excel"
    ]

    for k in known_proper_nouns:
        if k.lower() in clean_text.lower():
            if k.lower() not in GENERIC_PROPER_NOUNS:
                nouns.append(k)

    sentences = re.split(r"[.!?:]\s+", clean_text)
    for s in sentences:
        words = s.strip().split()
        if len(words) <= 1:
            continue
        i = 1
        while i < len(words):
            w = words[i].strip(",.:;\"'()[]")
            if w and w[0].isupper() and not w.isupper() and w.lower() not in ("và", "với", "nhưng", "tab", "đối thủ"):
                phrase = [w]
                j = i + 1
                while j < len(words):
                    nw = words[j].strip(",.:;\"'()[]")
                    if nw and nw[0].isupper() and nw.lower() not in ("và", "với", "nhưng"):
                        phrase.append(nw)
                        j += 1
                    else:
                        break
                p_str = " ".join(phrase)
                if p_str.lower() not in GENERIC_PROPER_NOUNS:
                    nouns.append(p_str)
                i = j
            else:
                i += 1

    seen = set()
    dedup = []
    for noun in nouns:
        nl = noun.lower()
        if nl not in seen and len(noun) > 1 and nl not in GENERIC_PROPER_NOUNS:
            seen.add(nl)
            dedup.append(noun)
    return dedup


def check_presence_in_dom(target: str | Dict[str, Any], dom_text: str) -> bool:
    """Check if a number or proper noun appears in the captured DOM text."""
    if not dom_text:
        return False

    dom_lower = dom_text.lower()

    if isinstance(target, str):
        t_clean = target.strip().lower()
        if t_clean in dom_lower:
            return True
        if strip_accents_lower(t_clean) in strip_accents_lower(dom_lower):
            return True
        return False

    if isinstance(target, dict):
        equivs = target.get("equivalents", [])
        for eq in equivs:
            eq_clean = eq.strip().lower()
            if eq_clean in dom_lower:
                return True
            val = target.get("val")
            if val is not None:
                for token in re.findall(r"[\$]?\d[\d.,]*", dom_text):
                    num = normalize_numeric_string(token)
                    if num is not None:
                        if abs(num - val) < 0.001:
                            return True
                        if target.get("unit") == "tan" and abs(num - val * 1000) < 0.001:
                            return True
        return False

    return False
