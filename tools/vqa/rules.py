"""Rules loader for VQA."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_RULES = {
    "profile": "stradevn",
    "max_seconds": 115,
    "safe_zones": {
        "top": 150,
        "bottom": 420,
        "right": 140,
        "width": 1080,
        "height": 1920,
    },
    "viewport": {
        "fullbleed": [1080, 1350],
        "card": [720, 1080],
    },
    "forbidden_phrases": [
        "tờ khai hải quan",
        "tờ khai",
        "importgenius",
        "panjiva",
        "volza",
        "trademo",
        "importkey",
        "datamyne",
        "descartes",
        "ihs markit",
        "sp global",
        "enigma",
        "seair",
        "infodrive",
    ],
    "disallow_emoji_in_badges": True,
    "required_phrases": [
        "dữ liệu xuất nhập khẩu toàn cầu",
    ],
    "voice": {
        "min_profile_words": 40,
        "require_unique_directions": True,
        "require_word_numbers": True,
    },
    "loop": {
        "require_colon_or_lead_end": True,
        "require_same_scene_rec_mark": True,
        "max_seam_pixel_diff": 25.0,
    },
    "pii": {
        "private_emails": [
            "stradevn@gmail.com",
            "owner@stradevn.com",
            "admin@stradevn.com",
        ],
        "private_phones": [
            "090411",
            "0987654321",
        ],
        "private_names": [
            "Nguyễn Hoàng",
            "Hoàng Nguyễn",
        ],
        "forbidden_email_patterns": [
            r"@gmail\.com",
        ],
        "allowed_emails": [
            "customerservice@stcharlestrading.com",
        ],
    },
    "marks": {
        "max_ink_per_scene": 2,
    },
    "stickers": {
        "min_spacing_seconds": 10.0,
        "none_before_seconds": 3.0,
    },
    "audio": {
        "target_lufs": -14.0,
        "lufs_tolerance": 1.5,
        "max_true_peak": -1.0,
        "max_black_duration": 0.3,
    },
}


def find_repo_root(start: Path) -> Path:
    """Find repository root by looking for profiles/ or .git."""
    curr = start.resolve()
    for _ in range(6):
        if (curr / "profiles").is_dir() or (curr / ".git").is_dir():
            return curr
        if curr.parent == curr:
            break
        curr = curr.parent
    return start.resolve()


def load_rules(clip_dir: Path | str, profile_name: Optional[str] = None) -> Dict[str, Any]:
    """Load profile rules for the given clip."""
    clip_path = Path(clip_dir).resolve()
    repo_root = find_repo_root(clip_path)

    if not profile_name:
        clip_json_path = clip_path / "clip.json"
        if clip_json_path.exists():
            try:
                data = json.loads(clip_json_path.read_text(encoding="utf-8"))
                profile_name = data.get("profile")
            except Exception:
                pass
    if not profile_name:
        profile_name = "stradevn"

    rules_path = repo_root / "profiles" / profile_name / "rules.json"
    rules = dict(DEFAULT_RULES)

    if rules_path.exists():
        try:
            custom = json.loads(rules_path.read_text(encoding="utf-8"))
            _deep_update(rules, custom)
        except Exception:
            pass

    return rules


def _deep_update(base: dict, update: dict):
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
