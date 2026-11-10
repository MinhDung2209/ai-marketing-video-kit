"""Kiểm tra thời điểm và mật độ của accent SFX (riser, hit, va chạm meme, trần mật độ).

Luật:
  1. Riser kết thúc trong khoảng 0.15s quanh mốc reveal của nó (riser ends within 0.15s of its reveal).
  2. Không có 2 accent nào cách nhau dưới 0.6s (trừ riser và hit của cùng 1 reveal).
  3. Không có accent nào nằm trong vùng đè hoặc cách meme dưới 0.6s.
  4. Mật độ SFX trong giới hạn (<= 1 accent / ~4s, tức tối đa 15 accents/phút).
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check


def _is_accent_sfx(file_name: str, label: str = "") -> bool:
    """Xác định xem một SFX có phải là accent (hit, impact, riser, chime, sparkle, pop) không."""
    fn = (file_name or "").lower()
    lbl = (label or "").lower()
    # Loại trừ typing, click liên tục, và whoosh chuyển cảnh thông thường
    if any(k in fn for k in ("typing", "click", "mouse")):
        return False
    return any(k in fn or k in lbl for k in ("riser", "impact", "hit", "chime", "sparkle", "bell", "pop", "accent"))


@register_check(stage="build", name="sfx_timing")
def check_sfx_timing(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []

    cues = ctx.cues_json
    if not cues:
        return issues

    duration = float(cues.get("duration", 0.0))
    sfx_list = cues.get("sfx", [])

    # Load sound_plan.json nếu có
    sound_plan_file = ctx.clip_dir / "sound_plan.json"
    sound_plan = None
    if sound_plan_file.exists():
        try:
            sound_plan = json.loads(sound_plan_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 1. Tìm các meme (thời gian bắt đầu, độ dài)
    memes: List[Tuple[float, float, str]] = []
    # Từ index.html (thẻ sticker có class stk hoặc video meme)
    if ctx.index_html:
        stk_matches = re.findall(
            r'class=[\'"][^\'"]*stk[^\'"]*[\'"][^>]+data-start=[\'"]([\d.]+)[\'"][^>]+data-duration=[\'"]([\d.]+)[\'"]',
            ctx.index_html,
        )
        for s, d in stk_matches:
            memes.append((float(s), float(d), "sticker"))

    # Từ cues.json sfx (các file có meme: hoặc đường dẫn assets/meme)
    for s in sfx_list:
        f = str(s.get("file", ""))
        if "meme" in f.lower():
            t = float(s.get("t", 0.0))
            dur = float(s.get("dur", 2.0))
            memes.append((t, dur, f))

    # 2. Phân loại SFX và kiểm tra riser timing
    reveals = []
    if sound_plan and "reveals" in sound_plan:
        reveals = sound_plan["reveals"]

    accents: List[Dict[str, Any]] = []
    risers: List[Dict[str, Any]] = []

    for s in sfx_list:
        fn = str(s.get("file", ""))
        lbl = str(s.get("label", ""))
        t = float(s.get("t", 0.0))
        dur = float(s.get("dur", 0.0))
        offset = float(s.get("offset", 0.0))
        target = s.get("reveal_target")

        if "riser" in fn.lower() or "riser" in lbl.lower() or s.get("kind") == "riser":
            risers.append(s)
        elif _is_accent_sfx(fn, lbl):
            accents.append(s)

    # Kiểm tra 1: Riser timing (kết thúc trong vòng 0.15s quanh mốc reveal)
    for r in risers:
        r_t = float(r.get("t", 0.0))
        r_dur = float(r.get("dur", 0.0))
        r_end = r_t + r_dur
        target = r.get("reveal_target")

        # Nếu không có explicit reveal_target, tìm reveal gần nhất hoặc hit gần nhất sau riser
        if target is None:
            # Tìm trong reveals
            cand_targets = [float(rv["time"]) for rv in reveals if float(rv["time"]) >= r_t]
            if cand_targets:
                target = min(cand_targets, key=lambda ct: abs(ct - r_end))
            else:
                # Tìm hit SFX sau riser
                following_hits = [float(ac["t"]) for ac in accents if float(ac["t"]) >= r_t]
                if following_hits:
                    target = following_hits[0]

        if target is not None:
            diff = abs(r_end - float(target))
            if diff > 0.15:
                issues.append(
                    Issue(
                        check="sfx_timing",
                        where=f"riser @ {r_t:.2f}s (kết thúc {r_end:.2f}s)",
                        msg=f"Riser kết thúc lệch {diff:.2f}s so với mốc reveal {float(target):.2f}s (> 0.15s)",
                        fix_hint="Điều chỉnh thời điểm bắt đầu riser = reveal_time - riser_duration (hoặc trim offset nếu chạm đầu clip).",
                    )
                )

    # Kiểm tra 2: Không có 2 accent nào < 0.6s apart
    # (Loại trừ trường hợp riser kết thúc và hit nổ ngay tại mốc reveal đó)
    all_accents_sorted = sorted(
        [s for s in sfx_list if _is_accent_sfx(str(s.get("file", "")), str(s.get("label", "")))],
        key=lambda x: float(x.get("t", 0.0)),
    )
    for i in range(len(all_accents_sorted) - 1):
        a1 = all_accents_sorted[i]
        a2 = all_accents_sorted[i + 1]
        t1, t2 = float(a1.get("t", 0.0)), float(a2.get("t", 0.0))
        # Nếu a1 là riser và a2 là hit tại điểm kết thúc của riser thì là cặp hợp lệ
        is_riser_hit_pair = ("riser" in str(a1.get("file", "")).lower() or a1.get("kind") == "riser") and abs(t1 + float(a1.get("dur", 0)) - t2) <= 0.15
        if not is_riser_hit_pair and (t2 - t1) < 0.6:
            issues.append(
                Issue(
                    check="sfx_timing",
                    where=f"accents @ {t1:.2f}s và {t2:.2f}s",
                    msg=f"Hai accent SFX quá gần nhau ({t2 - t1:.2f}s < 0.6s)",
                    fix_hint="Giữ khoảng cách tối thiểu 0.6s giữa các accent SFX để tránh dồn dập, tranh chấp âm lượng.",
                )
            )

    # Kiểm tra 3: Không có accent nào đè hoặc cách meme < 0.6s
    for a in all_accents_sorted:
        at = float(a.get("t", 0.0))
        for mt, mdur, mname in memes:
            if (mt - 0.6) <= at <= (mt + mdur + 0.6):
                issues.append(
                    Issue(
                        check="sfx_timing",
                        where=f"accent @ {at:.2f}s gần meme @ {mt:.2f}s–{mt+mdur:.2f}s",
                        msg=f"Accent SFX ({a.get('file')}) nằm đè hoặc cách meme dưới 0.6s",
                        fix_hint="Dời hoặc bỏ accent SFX tại khu vực meme để không phá vỡ nhịp của meme.",
                    )
                )
                break

    # Kiểm tra 4: Mật độ SFX trong giới hạn (<= 1 accent / ~4s)
    # Tương đương tối đa duration / 4 + 1 accents trong toàn clip
    if duration > 0:
        max_allowed_accents = max(2, int(duration / 4.0) + 1)
        accent_count = len(accents) + len(risers)
        if accent_count > max_allowed_accents:
            issues.append(
                Issue(
                    check="sfx_timing",
                    where=f"toàn clip ({duration:.1f}s)",
                    msg=f"Mật độ accent SFX quá dày ({accent_count} accents, giới hạn tối đa {max_allowed_accents} theo quy tắc <= 1 / 4s)",
                    fix_hint="Lọc bớt các accent không cần thiết, chỉ giữ riser/hit ở các mốc reveal thật sự quan trọng.",
                )
            )

    return issues
