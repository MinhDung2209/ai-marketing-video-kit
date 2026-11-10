"""Thực thi và quản lý vòng lặp Gate QA / Dryrun với cơ chế phản hồi lỗi cho LLM."""
import json
import pathlib
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

KIT = pathlib.Path(__file__).resolve().parent.parent.parent


def run_gate(
    script_rel_path: str,
    args: List[str],
    cwd: Optional[pathlib.Path] = None,
    stage_name: str = "",
) -> Dict[str, Any]:
    """Chạy một gate script (ví dụ tools/vqa/run.py hoặc screendemo/dryrun.py).

    Nếu file script chưa tồn tại (đang được viết song song), bỏ qua và trả về skipped=True.
    """
    script_path = KIT / script_rel_path
    if not script_path.exists():
        print(f"  [GATE {stage_name}] ⚠ Chưa có file {script_rel_path} → tạm bỏ qua kiểm tra.", file=sys.stderr)
        return {
            "ok": True,
            "skipped": True,
            "errors": [],
            "warnings": [f"Gate script {script_rel_path} chưa được cài đặt."],
        }

    cmd = [sys.executable, "-X", "utf8", str(script_path), *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or KIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out_txt = proc.stdout.strip()
        # Tìm dòng JSON cuối cùng trong stdout
        json_line = None
        for line in reversed(out_txt.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                json_line = line
                break

        if json_line:
            data = json.loads(json_line)
            return data
        else:
            if proc.returncode == 0:
                return {"ok": True, "errors": [], "warnings": []}
            return {
                "ok": False,
                "errors": [
                    {
                        "check": "execution_failed",
                        "where": stage_name,
                        "msg": proc.stderr or proc.stdout,
                        "fix_hint": "Kiểm tra cú pháp hoặc tham số đầu vào.",
                    }
                ],
            }
    except Exception as e:
        return {
            "ok": False,
            "errors": [
                {
                    "check": "system_error",
                    "where": stage_name,
                    "msg": str(e),
                    "fix_hint": "Xem log lỗi hệ thống.",
                }
            ],
        }


def format_gate_feedback(errors: List[Dict[str, Any]]) -> str:
    """Định dạng các lỗi gate thành chuỗi nhắc nhở cho LLM."""
    lines = ["Gate kiểm tra phát hiện các lỗi sau:"]
    for err in errors:
        check = err.get("check", "unknown")
        where = err.get("where", "")
        msg = err.get("msg", "")
        fix = err.get("fix_hint", "")
        lines.append(f"- [{check}] Tại '{where}': {msg}")
        if fix:
            lines.append(f"  * Gợi ý sửa: {fix}")
    lines.append("Hãy cập nhật và sửa lại file JSON để khắc phục toàn bộ các lỗi trên.")
    return "\n".join(lines)


def run_stage_with_gate_loop(
    stage_name: str,
    llm_generator: Callable[[Optional[str]], Any],
    gate_checker: Callable[[], Dict[str, Any]],
    max_retries: int = 3,
) -> Any:
    """Thực thi một stage với vòng lặp thử lại tối đa max_retries khi gate trả về lỗi."""
    feedback = None
    last_gate_res = None

    for attempt in range(max_retries):
        print(f"--- [Stage {stage_name}] Lần thử {attempt + 1}/{max_retries} ---")
        llm_res = llm_generator(feedback)

        gate_res = gate_checker()
        last_gate_res = gate_res

        if gate_res.get("ok"):
            if gate_res.get("skipped"):
                print(f"✅ [Stage {stage_name}] Hoàn tất (Gate tạm bỏ qua)")
            else:
                print(f"✅ [Stage {stage_name}] Đạt Gate kiểm tra!")
            return llm_res

        errors = gate_res.get("errors", [])
        print(f"❌ [Stage {stage_name}] Gate thất bại: {len(errors)} lỗi.")
        for e in errors:
            print(f"   * {e.get('where')}: {e.get('msg')}")

        feedback = format_gate_feedback(errors)

    err_summary = json.dumps(last_gate_res.get("errors", []), ensure_ascii=False, indent=2)
    raise RuntimeError(
        f"Stage '{stage_name}' dừng lại sau {max_retries} lần thử không qua được Gate.\nLỗi chi tiết:\n{err_summary}"
    )
