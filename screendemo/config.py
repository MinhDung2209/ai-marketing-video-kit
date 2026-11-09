"""Cấu hình máy cho screendemo: kit/config.json → khối "screendemo" (KHÔNG commit config.json).
  "screendemo": {"cdp": "http://127.0.0.1:9333",                       # cổng debug của Chrome quay video
                 "chrome": "D:/Apps/Google/Chrome/Application/chrome.exe", # Chrome dùng để render
                 "ffmpeg": "D:/Apps/ffmpeg/bin/ffmpeg.exe"}"""
import json, pathlib
KIT = pathlib.Path(__file__).resolve().parent.parent


def cfg():
    try: return json.loads((KIT / "config.json").read_text(encoding="utf-8")).get("screendemo", {})
    except Exception: return {}
