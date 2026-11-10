"""Tạo ảnh Qwen-Image qua workflow ComfyUI dạng API có placeholder."""
import argparse
import json
from pathlib import Path
import sys
import time

import requests

from find_sources import KIT, TIMEOUT, UA, get, read_json


def render(prompt, output, config, width=1344, height=768, seed=42, wait=600):
    workflow_path = Path(config["comfyui_workflow"])
    if not workflow_path.is_absolute():
        workflow_path = KIT / workflow_path
    workflow = read_json(workflow_path)
    if not isinstance(workflow, dict) or "nodes" in workflow:
        raise ValueError("Cần workflow Qwen-Image xuất dạng API, không phải UI JSON")
    values = {"{{prompt}}": prompt, "{{width}}": width, "{{height}}": height, "{{seed}}": seed}
    used = set()

    def substitute(value):
        if isinstance(value, str) and value in values:
            used.add(value)
            return values[value]
        if isinstance(value, dict):
            return {k: substitute(v) for k, v in value.items()}
        if isinstance(value, list):
            return [substitute(v) for v in value]
        return value

    workflow = substitute(workflow)
    if used != set(values):
        raise ValueError("Workflow cần đủ {{prompt}}, {{width}}, {{height}}, {{seed}}")
    base = config["comfyui_url"].rstrip("/")
    response = requests.post(base + "/prompt", json={"prompt": workflow},
                             headers={"User-Agent": UA}, timeout=TIMEOUT)
    response.raise_for_status()
    result = response.json()
    if result.get("node_errors"):
        raise ValueError("ComfyUI từ chối workflow")
    prompt_id = result["prompt_id"]
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        job = get(base + "/history/" + prompt_id).json().get(prompt_id, {})
        if job.get("status", {}).get("status_str") == "error":
            raise ValueError("ComfyUI tạo ảnh thất bại")
        for node in job.get("outputs", {}).values():
            for item in node.get("images", []):
                if item.get("type", "output") != "output":
                    continue
                response = get(base + "/view", params={k: item[k] for k in ("filename", "subfolder", "type") if k in item})
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(response.content)
                print(f"Đã tạo ảnh: {output}")
                return output
        time.sleep(2)
    raise TimeoutError(f"ComfyUI chưa xong sau {wait}s; prompt_id={prompt_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("out", type=Path)
    parser.add_argument("--width", type=int, default=1344)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--wait", type=int, default=600)
    args = parser.parse_args()
    if min(args.width, args.height, args.wait) <= 0:
        parser.error("width, height, wait phải lớn hơn 0")
    try:
        render(args.prompt, args.out, read_json(KIT / "config.json", {}), args.width, args.height, args.seed, args.wait)
    except (OSError, KeyError, ValueError, requests.RequestException) as exc:
        print(f"Lỗi ComfyUI ({type(exc).__name__}); kiểm tra cấu hình / workflow.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
