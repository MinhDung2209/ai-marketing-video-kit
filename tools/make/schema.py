"""Quản lý và xác thực dữ liệu qua JSON Schema."""
import json
import pathlib
from typing import Any, Optional, Tuple

import jsonschema

KIT = pathlib.Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = KIT / "schemas"


def load_schema(name: str) -> dict:
    """Đọc schema từ schemas/<name>.schema.json hoặc schemas/<name>.json."""
    if not name.endswith(".json"):
        candidates = [
            SCHEMAS_DIR / f"{name}.schema.json",
            SCHEMAS_DIR / f"{name}.json",
        ]
    else:
        candidates = [SCHEMAS_DIR / name]

    for c in candidates:
        if c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Không tìm thấy schema {name} trong {SCHEMAS_DIR}")


def validate_data(data: Any, schema_name_or_dict: Any) -> Tuple[bool, Optional[str]]:
    """Xác thực đối tượng data với schema. Trả về (True, None) nếu hợp lệ, (False, lỗi) nếu sai."""
    schema = (
        load_schema(schema_name_or_dict)
        if isinstance(schema_name_or_dict, str)
        else schema_name_or_dict
    )
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True, None
    except jsonschema.ValidationError as e:
        loc = " -> ".join(str(p) for p in e.absolute_path) or "root"
        msg = f"Lỗi schema tại '{loc}': {e.message}"
        return False, msg
    except Exception as e:
        return False, str(e)
