"""Kiểm tra an toàn kịch bản thao tác trước khi quay (forbidden steps)."""
import json
import pathlib
from typing import Any, Dict, List, Optional, Tuple

FORBIDDEN_KEYWORDS = [
    "tạo chiến dịch",
    "bắt đầu truy xuất",
    "cách gửi",
    "xác nhận gửi",
    "xác nhận",
    "dùng nội dung đang soạn để bật lịch",
    "gửi ngay",
    "send email",
    "xoá chiến dịch",
    "xóa chiến dịch",
]


def extract_target_text(target: Any) -> str:
    """Rút trích các chuỗi văn bản nhận diện từ target của step."""
    if isinstance(target, str):
        return target.lower()
    if isinstance(target, dict):
        parts = []
        for k in ("text", "has_text", "name", "after_label", "css"):
            v = target.get(k)
            if isinstance(v, str):
                parts.append(v.lower())
        return " ".join(parts)
    return ""


def check_forbidden_steps(
    shots_data: Dict[str, Any], profile_data: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[Dict[str, str]]]:
    """Kiểm tra toàn bộ các shot trong shots.json xem có bấm nút bị cấm không.

    Trả về (ok, errors).
    errors có định dạng: [{"check": "forbidden_click", "where": "s1/step 2", "msg": "...", "fix_hint": "..."}]
    """
    errors = []
    never_click = list(FORBIDDEN_KEYWORDS)

    if profile_data:
        prof_never = profile_data.get("safety", {}).get("never_click", [])
        for item in prof_never:
            if isinstance(item, str) and item.lower() not in never_click:
                never_click.append(item.lower())

    shots = shots_data.get("shots", {})
    for shot_id, shot_info in shots.items():
        steps = shot_info.get("steps", [])
        for idx, step in enumerate(steps):
            do = step.get("do", "")
            target_str = extract_target_text(step.get("target"))

            if do == "click":
                for bad in never_click:
                    if bad in target_str:
                        errors.append(
                            {
                                "check": "forbidden_click",
                                "where": f"shot '{shot_id}' step #{idx} (do: click)",
                                "msg": f"Cấm click vào mục tiêu chứa '{bad}' (vi phạm luật an toàn).",
                                "fix_hint": f"Bỏ thao tác click vào '{bad}', chỉ dừng ở bước xem trước hoặc chọn bảng.",
                            }
                        )

            # Kiểm tra url goto có gọi lệnh cấm
            if do == "goto":
                url = str(step.get("url", "")).lower()
                if "delete" in url or "destroy" in url:
                    errors.append(
                        {
                            "check": "forbidden_action",
                            "where": f"shot '{shot_id}' step #{idx} (do: goto)",
                            "msg": f"URL nguy hiểm: {url}",
                            "fix_hint": "Không điều hướng tới endpoint xoá dữ liệu.",
                        }
                    )

    return len(errors) == 0, errors
