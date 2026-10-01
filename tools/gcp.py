"""Lấy access token Google Cloud từ service account (dùng chung cho TTS, Lyria, Veo...).

Đường dẫn file key (JSON service account) tìm theo thứ tự:
1. biến môi trường VIDEOKIT_GCP_KEY
2. "gcp_key_path" trong kit/config.json (chép từ kit/config.example.json)
KHÔNG chép file key vào kit/ hay vào gói đóng gói — chỉ trỏ tới nơi nó đang nằm.
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import json, os, pathlib
import google.auth.transport.requests
from google.oauth2 import service_account

KIT = pathlib.Path(__file__).resolve().parent.parent

def config():
    p = KIT / "config.json"
    return json.load(open(p, encoding="utf-8")) if p.exists() else {}

def key_path():
    k = os.environ.get("VIDEOKIT_GCP_KEY") or config().get("gcp_key_path")
    if not k or not pathlib.Path(k).exists():
        raise SystemExit("Chưa có key Google Cloud: đặt biến VIDEOKIT_GCP_KEY hoặc 'gcp_key_path' trong kit/config.json "
                         "(xem kit/docs/01-cai-dat.md).")
    return k

def token_and_project():
    k = key_path()
    c = service_account.Credentials.from_service_account_file(k, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    c.refresh(google.auth.transport.requests.Request())
    return c.token, json.load(open(k, encoding="utf-8"))["project_id"]
