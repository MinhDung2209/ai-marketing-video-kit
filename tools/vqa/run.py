#!/usr/bin/env python3
"""CLI entry point for VQA (Screen-demo Video Automatic QA / Lint).

Contract:
  python tools/vqa/run.py <clip_dir> --stage brief|shots|build|render [--json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Ensure repo root is on sys.path
KIT_ROOT = Path(__file__).resolve().parents[2]
if str(KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(KIT_ROOT))

from tools.vqa.runner import run_stage
from tools.vqa.rules import load_rules


def main():
    parser = argparse.ArgumentParser(description="VQA: Automatic QA/lint for screen-demo videos")
    parser.add_argument("clip_dir", help="Path to clip directory")
    parser.add_argument(
        "--stage",
        required=True,
        choices=["brief", "shots", "build", "render"],
        help="Stage to QA (brief | shots | build | render)",
    )
    parser.add_argument("--json", action="store_true", help="Print structured JSON result")
    parser.add_argument("--profile", default=None, help="Profile name override (defaults to clip.json or stradevn)")

    args = parser.parse_args()
    clip_path = Path(args.clip_dir).resolve()

    if not clip_path.exists():
        err_res = {
            "ok": False,
            "stage": args.stage,
            "errors": [
                {
                    "check": "clip_dir",
                    "where": str(clip_path),
                    "msg": f"Thư mục clip không tồn tại: {clip_path}",
                    "fix_hint": "Kiểm tra lại đường dẫn thư mục clip.",
                }
            ],
            "warnings": [],
        }
        if args.json:
            print(json.dumps(err_res, ensure_ascii=False, indent=2))
        else:
            print(f"❌ Thư mục không tồn tại: {clip_path}")
        sys.exit(1)

    rules = load_rules(clip_path, profile_name=args.profile)
    result = run_stage(clip_path, stage=args.stage, rules=rules)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status_icon = "✅" if result["ok"] else "❌"
        print(f"\n{status_icon} VQA STAGE: {args.stage.upper()} · Clip: {clip_path.name}")
        print(f"   Trạng thái: {'ĐẠT (OK)' if result['ok'] else 'CẦN SỬA (FAILED)'}")
        print(f"   Lỗi (Errors): {len(result['errors'])} · Cảnh báo (Warnings): {len(result['warnings'])}\n")

        if result["errors"]:
            print("🔴 DANH SÁCH LỖI (ERRORS):")
            for idx, err in enumerate(result["errors"], 1):
                print(f"  {idx}. [{err['check']}] Tại: {err['where']}")
                print(f"     Nội dung: {err['msg']}")
                print(f"     Hướng sửa: {err['fix_hint']}\n")

        if result["warnings"]:
            print("🟡 CẢNH BÁO (WARNINGS):")
            for idx, warn in enumerate(result["warnings"], 1):
                print(f"  {idx}. [{warn['check']}] Tại: {warn['where']}")
                print(f"     Nội dung: {warn['msg']}")
                print(f"     Hướng sửa: {warn['fix_hint']}\n")

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
