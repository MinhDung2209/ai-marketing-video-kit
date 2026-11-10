"""Check for PII (personally identifiable information) leaks in captured DOM text."""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, register_check

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+84|0)[3|5|7|8|9]\d{8}\b")


@register_check(stage="shots", name="pii_scan")
def check_pii_scan(ctx: VQAContext) -> List[Issue]:
    issues: List[Issue] = []
    pii_rules = ctx.rules.get("pii", {})
    private_emails = [e.lower() for e in pii_rules.get("private_emails", [])]
    private_phones = [p for p in pii_rules.get("private_phones", [])]
    private_names = [n.lower() for n in pii_rules.get("private_names", [])]
    allowed_emails = [e.lower() for e in pii_rules.get("allowed_emails", [])]
    forbidden_patterns = [re.compile(pat, re.I) for pat in pii_rules.get("forbidden_email_patterns", [])]

    screen_dir = ctx.clip_dir / "assets" / "screen"
    if not screen_dir.is_dir():
        return issues

    for shot_dir in screen_dir.iterdir():
        if not shot_dir.is_dir() or shot_dir.name.startswith(("_", ".")):
            continue
        shot_id = shot_dir.name
        marks = ctx.get_shot_marks(shot_id)

        # 1. Check each mark's element_text and page_text_path
        for mark in marks:
            mark_name = mark.get("name", "unnamed")
            texts_to_check = []

            if mark.get("element_text"):
                texts_to_check.append(("element_text", mark["element_text"]))

            if mark.get("page_text_path"):
                p = shot_dir / mark["page_text_path"]
                if p.exists():
                    try:
                        texts_to_check.append((f"snapshot {p.name}", p.read_text(encoding="utf-8")))
                    except Exception:
                        pass

            for src_label, txt in texts_to_check:
                txt_lower = txt.lower()

                # Check exact private emails
                for pe in private_emails:
                    if pe in txt_lower:
                        issues.append(
                            Issue(
                                check="pii_scan",
                                where=f"assets/screen/{shot_id}/{mark_name} ({src_label})",
                                msg=f"Lộ email cá nhân của chủ dự án: {pe}",
                                fix_hint="Che hoặc đăng xuất tài khoản cá nhân trong Chrome quay video; không quay tab chứa Gmail cá nhân.",
                            )
                        )

                # Check forbidden patterns (e.g. any @gmail.com)
                found_emails = EMAIL_RE.findall(txt)
                for em in found_emails:
                    em_lower = em.lower()
                    if em_lower in allowed_emails:
                        continue
                    for pat in forbidden_patterns:
                        if pat.search(em_lower):
                            issues.append(
                                Issue(
                                    check="pii_scan",
                                    where=f"assets/screen/{shot_id}/{mark_name} ({src_label})",
                                    msg=f"Lộ địa chỉ email cá nhân ({em}) theo mẫu cấm",
                                    fix_hint="Dùng email doanh nghiệp công khai thay vì Gmail cá nhân trên màn hình quay.",
                                )
                            )

                # Check private phones
                for ph in private_phones:
                    if ph in txt:
                        issues.append(
                            Issue(
                                check="pii_scan",
                                where=f"assets/screen/{shot_id}/{mark_name} ({src_label})",
                                msg=f"Lộ số điện thoại riêng: {ph}",
                                fix_hint="Che số điện thoại cá nhân trên giao diện web khi quay.",
                            )
                        )

                # Check private names
                for pn in private_names:
                    if pn in txt_lower:
                        issues.append(
                            Issue(
                                check="pii_scan",
                                where=f"assets/screen/{shot_id}/{mark_name} ({src_label})",
                                msg=f"Lộ tên riêng của chủ sở hữu: {pn}",
                                fix_hint="Ẩn tên người dùng/avatar tài khoản cá nhân ở góc giao diện.",
                            )
                        )

        # 2. Check snapshot files directly in _dom/
        dom_dir = shot_dir / "_dom"
        if dom_dir.is_dir():
            for txt_file in dom_dir.glob("*.txt"):
                try:
                    content = txt_file.read_text(encoding="utf-8").lower()
                    for pe in private_emails:
                        if pe in content:
                            issues.append(
                                Issue(
                                    check="pii_scan",
                                    where=f"assets/screen/{shot_id}/_dom/{txt_file.name}",
                                    msg=f"Lộ email cá nhân trong DOM snapshot: {pe}",
                                    fix_hint="Không hiển thị Gmail cá nhân trong bản quay.",
                                )
                            )
                except Exception:
                    pass

    return issues
