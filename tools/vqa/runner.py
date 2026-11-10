"""VQA stage runner."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.vqa.context import VQAContext
from tools.vqa.registry import Issue, get_checks
from tools.vqa.rules import load_rules


def run_stage(
    clip_dir: Path | str,
    stage: str,
    rules: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute all checks registered for a stage against a clip directory."""
    ctx = VQAContext(clip_dir=clip_dir, rules=rules)
    checks = get_checks(stage)

    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    for check_def in checks:
        try:
            issues = check_def.func(ctx)
            for iss in issues:
                if iss.level == "warning":
                    warnings.append(iss.to_dict())
                else:
                    errors.append(iss.to_dict())
        except Exception as exc:
            errors.append({
                "check": check_def.name,
                "where": f"{stage} check runner",
                "msg": f"Check {check_def.name} gặp lỗi runtime: {exc}",
                "fix_hint": "Kiểm tra lại cấu hình hoặc dữ liệu đầu vào của clip.",
            })

    ok = len(errors) == 0
    return {
        "ok": ok,
        "stage": stage,
        "errors": errors,
        "warnings": warnings,
    }
