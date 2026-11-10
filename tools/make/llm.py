"""Bộ điều hợp mô hình LLM (agy, codex, claude) và xử lý sinh JSON có kiểm tra schema."""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

from .schema import validate_data

KIT = pathlib.Path(__file__).resolve().parent.parent.parent

# Mock handler cho unit test
_MOCK_HANDLER: Optional[Callable[[str, str, Optional[str]], Dict[str, Any]]] = None


def set_mock_handler(handler: Optional[Callable[[str, str, Optional[str]], Dict[str, Any]]]):
    global _MOCK_HANDLER
    _MOCK_HANDLER = handler


def find_executable(name: str) -> Optional[str]:
    """Tìm đường dẫn thực thi của công cụ CLI."""
    w = shutil.which(name)
    if w:
        return w
    known_paths = {
        "agy": [r"D:\Tools\Antigravity\agy.exe", r"C:\Users\hoang\AppData\Local\Programs\Antigravity\agy.exe"],
        "codex": [r"D:\Tools\Codex\codex.cmd", r"C:\Users\hoang\AppData\Roaming\npm\codex.cmd"],
        "claude": [r"C:\Users\hoang\AppData\Roaming\npm\claude.cmd", "claude.exe"],
    }
    for cand in known_paths.get(name, []):
        if pathlib.Path(cand).exists():
            return cand
    return None


def extract_json_from_text(text: str) -> Optional[Any]:
    """Trích xuất khối JSON từ văn bản (code block hoặc raw JSON hoặc response wrapper)."""
    text = text.strip()
    # Thử parse toàn bộ văn bản
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "response" in obj and ("conversation_id" in obj or "status" in obj):
            inner = extract_json_from_text(obj["response"])
            if inner is not None:
                return inner
        return obj
    except Exception:
        pass

    # Thử tìm fenced block ```json ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass

    # Thử tìm khối JSON {} hoặc [] lớn nhất
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        first = text.find(start_char)
        last = text.rfind(end_char)
        if first != -1 and last != -1 and last > first:
            candidate = text[first : last + 1]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict) and "response" in obj and ("conversation_id" in obj or "status" in obj):
                    inner = extract_json_from_text(obj["response"])
                    if inner is not None:
                        return inner
                return obj
            except Exception:
                pass
    return None


def run_llm_process(
    model_spec: str,
    prompt: str,
    cwd: Optional[pathlib.Path] = None,
    timeout_sec: int = 300,
) -> str:
    """Gọi công cụ CLI (agy, codex, claude) và trả về stdout text."""
    parts = model_spec.split(":")
    engine = parts[0]
    sub_model = parts[1] if len(parts) > 1 else None

    if engine == "agy":
        exe = find_executable("agy") or "agy"
        cmd = [exe, "-p", prompt, "--output-format", "json", "--dangerously-skip-permissions"]
        if sub_model:
            cmd += ["--model", sub_model]
        proc = subprocess.run(
            cmd,
            cwd=cwd or KIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        return proc.stdout

    elif engine == "codex":
        exe = find_executable("codex") or "codex"
        cmd = [
            exe,
            "exec",
            "--skip-git-repo-check",
            "-s",
            "workspace-write",
            "-c",
            "sandbox_workspace_write.network_access=true",
            "--json",
            "-",
        ]
        if sub_model:
            cmd.insert(2, "-m")
            cmd.insert(3, sub_model)
        proc = subprocess.run(
            cmd,
            input=prompt,
            cwd=cwd or KIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        return proc.stdout

    elif engine == "claude":
        exe = find_executable("claude") or "claude"
        model_name = sub_model or "sonnet"
        cmd = [
            exe,
            "-p",
            prompt,
            "--model",
            model_name,
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            "Read",
            "Edit",
            "Write",
            "--output-format",
            "stream-json",
        ]
        proc = subprocess.run(
            cmd,
            cwd=cwd or KIT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
        return proc.stdout

    else:
        raise ValueError(f"Không hỗ trợ engine: {engine} (chọn agy, codex, hoặc claude)")


def generate_json(
    model_spec: str,
    prompt_file: pathlib.Path,
    target_file: pathlib.Path,
    schema_name: str,
    context_files: Optional[List[pathlib.Path]] = None,
    feedback: Optional[str] = None,
    cwd: Optional[pathlib.Path] = None,
    max_schema_retries: int = 3,
) -> Any:
    """Sinh file JSON bằng model adapter và kiểm tra chặt chẽ theo JSON schema.

    Nếu JSON không hợp lệ hoặc sai schema, nạp lại lỗi vào prompt và thử lại tối đa max_schema_retries.
    """
    if _MOCK_HANDLER is not None:
        return _MOCK_HANDLER(str(prompt_file), schema_name, feedback)

    prompt_body = prompt_file.read_text(encoding="utf-8")
    schema_path = KIT / "schemas" / f"{schema_name}.schema.json"
    schema_body = schema_path.read_text(encoding="utf-8") if schema_path.exists() else "{}"

    # Đọc các file ngữ cảnh
    ctx_text = []
    for f in context_files or []:
        if f.exists():
            ctx_text.append(f"--- Nội dung file {f.name} ---\n{f.read_text(encoding='utf-8')}\n")

    current_feedback = feedback

    for attempt in range(max_schema_retries):
        full_prompt = (
            f"{prompt_body}\n\n"
            f"=== JSON SCHEMA BẮT BUỘC (schema: {schema_name}) ===\n"
            f"{schema_body}\n\n"
            f"=== CÁC FILE NGỮ CẢNH DỰ ÁN ===\n"
            f"{''.join(ctx_text)}\n\n"
            f"=== YÊU CẦU ĐẦU RA ===\n"
            f"QUAN TRỌNG: KHÔNG sử dụng công cụ (tool), KHÔNG chạy lệnh terminal.\n"
            f"Hãy TRẢ VỀ TRỰC TIẾP nội dung JSON hợp lệ cho '{target_file.name}' trong khối ```json ... ```.\n"
            f"CHỈ TRẢ VỀ DUY NHẤT MÃ JSON HỢP LỆ THEO SCHEMA TRÊN, KHÔNG KÈM BẤT KỲ GIẢI THÍCH NGOÀI LỀ.\n"
        )
        if current_feedback:
            full_prompt += f"\n=== PHẢN HỒI LỖI TỪ LẦN CHẠY TRƯỚC (CẦN SỬA) ===\n{current_feedback}\n"

        stdout_txt = run_llm_process(model_spec, full_prompt, cwd=cwd)

        # 1. Kiểm tra file đích
        data = None
        if target_file.exists():
            try:
                data = json.loads(target_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # 2. Nếu file chưa có hoặc rỗng, tìm trong stdout
        if data is None and stdout_txt:
            data = extract_json_from_text(stdout_txt)
            if data is not None:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        if data is None:
            current_feedback = "Lỗi: Không tìm thấy nội dung JSON hợp lệ trong file đích hoặc đầu ra stdout. Hãy ghi lại JSON."
            continue

        # 3. Kiểm tra tính hợp lệ với JSON Schema
        ok, err_msg = validate_data(data, schema_name)
        if ok:
            return data

        print(f"  [LLM] ⚠ Lỗi xác thực schema {schema_name}: {err_msg} (lần thử {attempt + 1}/{max_schema_retries})")
        current_feedback = f"Lỗi xác thực JSON Schema:\n{err_msg}\nHãy sửa lại định dạng cho đúng 100% với schema."

    raise RuntimeError(
        f"Không thể sinh JSON hợp lệ cho '{schema_name}' sau {max_schema_retries} lần thử qua model {model_spec}."
    )
