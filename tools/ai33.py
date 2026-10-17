"""AI33 (api.ai33.pro): voice ElevenLabs/Minimax/Edge…, sound effect, nhạc Suno, ảnh — tạo xong tải file về.

Key: AI33_API_KEY (biến môi trường, .env của dự án hoặc kit/.env — mẫu kit/.env.example).
Lịch sử: task VOICE (tts, dialogue) được GIỮ trên AI33; mọi loại khác tải về xong là XÓA task luôn.

Dùng:
  python <kit>/tools/ai33.py credits
  python <kit>/tools/ai33.py voices "Adam" [--provider elevenlabs]
  python <kit>/tools/ai33.py tts "Câu đọc..." --voice elevenlabs_pNInz6obpgDQGcFmaJgB -o voice/V001.mp3 [--speed 1]
  python <kit>/tools/ai33.py tts --text-file doan1.txt --voice ... -o voice/doan1.mp3
  python <kit>/tools/ai33.py sfx "waves crashing on rocks" --seconds 5 -o sfx/waves.mp3      → tải xong xóa task
  python <kit>/tools/ai33.py music "calm acoustic guitar, travel" --instrumental -o music/   → tải xong xóa task
  python <kit>/tools/ai33.py image "prompt" [--model bytedance-seedream-4.5] -o img/         → tải xong xóa task
  python <kit>/tools/ai33.py clean [--yes] [--since 2026-10-17]   → liệt kê (và xóa với --yes) task không phải voice
        tạo từ ngày --since (mặc định 2026-10-17); task cũ hơn để nguyên
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, datetime, json, os, pathlib, random, time
import requests

KIT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://api.ai33.pro"
VOICE_TYPES = {"tts", "dialogue", "tts_dialogue"}   # loại task được giữ lịch sử
CLEAN_SINCE = "2026-10-17"   # clean chỉ đụng task tạo từ ngày này (giờ máy); trước đó để nguyên

def key():
    if os.environ.get("AI33_API_KEY"): return os.environ["AI33_API_KEY"]
    for env in (pathlib.Path(".env"), KIT / ".env"):
        if env.exists():
            for ln in env.read_text(encoding="utf-8").splitlines():
                k, _, v = ln.partition("=")
                if k.strip() == "AI33_API_KEY" and v.strip(): return v.strip()
    raise SystemExit("Thiếu AI33_API_KEY: đặt biến môi trường hoặc ghi vào .env của dự án / kit/.env.")

def call(method, path, **kw):
    """Gọi API; 429 / 503 server_busy → chờ Retry-After rồi thử lại (lùi dần + ngẫu nhiên)."""
    for i in range(6):
        r = requests.request(method, BASE + path, headers={"xi-api-key": key()}, timeout=120, **kw)
        busy = r.status_code == 503 and "server_busy" in r.text
        if r.status_code != 429 and not busy:
            if r.status_code >= 400: raise SystemExit(f"AI33 {r.status_code} {path}: {r.text[:300]}")
            return r.json()
        time.sleep(float(r.headers.get("Retry-After") or 2 ** i) + random.random())
    raise SystemExit(f"AI33 bận quá lâu: {path}")

def wait(task_id):
    while True:
        t = call("GET", f"/v1/task/{task_id}")
        if t["status"] == "done": return t
        if t["status"] in ("error", "failed"): raise SystemExit(f"Task {task_id} lỗi: {t.get('error_message')}")
        time.sleep(3)

def result_urls(meta):
    """URL file kết quả trong metadata (bỏ link stream xem trước và ảnh bìa Suno)."""
    if meta.get("all_audio_urls"): return meta["all_audio_urls"]
    if meta.get("audio_url"): return [meta["audio_url"]]
    out = []   # ảnh và loại khác: chưa rõ tên trường → gom mọi URL trừ link stream
    def walk(v, k=""):
        if isinstance(v, dict): [walk(x, kk) for kk, x in v.items()]
        elif isinstance(v, list): [walk(x, k) for x in v]
        elif isinstance(v, str) and v.startswith("http") and "stream" not in k: out.append(v)
    walk(meta)
    return list(dict.fromkeys(out))

def download(url, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, timeout=300, stream=True) as r:
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1 << 16): f.write(chunk)
    return out

def save(task, out, keep):
    """Tải mọi file của task về `out` (file hoặc thư mục); task không phải voice thì xóa sau khi tải."""
    urls = result_urls(task.get("metadata") or {})
    if not urls: raise SystemExit(f"Task {task['id']} xong nhưng không thấy file: {json.dumps(task.get('metadata'))[:300]}")
    out = pathlib.Path(out)
    files = []
    for i, u in enumerate(urls):
        ext = pathlib.Path(u.split("?")[0]).suffix or ".bin"
        if out.suffix and len(urls) == 1: dst = out
        elif out.suffix: dst = out.with_name(f"{out.stem}_{i + 1}{out.suffix}")
        else: dst = out / f"{task['id'][:8]}_{i + 1}{ext}"
        files.append(download(u, dst))
    for f in files:
        if f.stat().st_size == 0: raise SystemExit(f"File tải về rỗng, KHÔNG xóa task {task['id']}: {f}")
    print(f"✓ {task.get('type')} · {task.get('credit_cost')} credit →", *map(str, files), sep="\n  ")
    if not keep:
        call("POST", "/v1/task/delete", json={"task_ids": [task["id"]]})
        print(f"  đã xóa task {task['id']} trên AI33")

def cmd_tts(a):
    text = pathlib.Path(a.text_file).read_text(encoding="utf-8") if a.text_file else a.text
    if not text: raise SystemExit("Cần lời đọc: tts \"...\" hoặc --text-file")
    r = call("POST", "/v3/text-to-speech", files={k: (None, str(v)) for k, v in
             {"text": text, "voice_id": a.voice, "speed": a.speed}.items()})
    save(wait(r["task_id"]), a.out, keep=True)

def cmd_sfx(a):
    body = {"text": a.prompt, "prompt_influence": a.influence, "loop": a.loop, "model_id": "eleven_text_to_sound_v2"}
    if a.seconds: body["duration_seconds"] = a.seconds
    r = call("POST", "/v1/task/sound-effect", json=body)
    save(wait(r["task_id"]), a.out, keep=False)

def cmd_music(a):
    r = call("POST", "/v1s/task/music-generation", json={"create_mode": "simple",
             "gpt_description_prompt": a.prompt, "make_instrumental": a.instrumental})
    save(wait(r["task_id"]), a.out, keep=False)

def cmd_image(a):
    r = call("POST", "/v1i/task/generate-image", files={k: (None, v) for k, v in {"prompt": a.prompt,
             "model_id": a.model, "generations_count": "1",
             "model_parameters": json.dumps({"aspect_ratio": a.aspect, "resolution": a.resolution})}.items()})
    save(wait(r["task_id"]), a.out, keep=False)

def cmd_credits(a):
    print(call("GET", "/v1/credits")["credits"], "credit")

def cmd_voices(a):
    d = call("GET", "/v3/voices", params={"provider": a.provider, "search": a.query, "limit": 30})
    for v in d["data"]:
        print(v["voice_id"], "|", v.get("name"), "|", v.get("gender"), v.get("age"), v.get("accent"))

def local_day(iso):
    return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().date().isoformat()

def cmd_clean(a):
    junk, page = [], 1
    while True:
        d = call("GET", "/v1/tasks", params={"page": page, "limit": 100})
        junk += [t for t in d["data"] if t.get("type") not in VOICE_TYPES and t.get("status") != "doing"
                 and local_day(t["created_at"]) >= a.since]
        if page * 100 >= int(d.get("total", 0)) or not d["data"]: break
        page += 1
    for t in junk: print(t.get("type"), t.get("status"), t["id"], t.get("created_at"))
    if not junk: return print(f"Không còn task nào ngoài voice tạo từ {a.since}.")
    if not a.yes: return print(f"{len(junk)} task không phải voice — chạy lại với --yes để xóa (file chưa tải sẽ mất).")
    for i in range(0, len(junk), 50):
        call("POST", "/v1/task/delete", json={"task_ids": [t["id"] for t in junk[i:i + 50]]})
    print(f"Đã xóa {len(junk)} task.")

p = argparse.ArgumentParser(description="AI33: voice giữ lịch sử, SFX/nhạc/ảnh tải xong xóa task")
sp = p.add_subparsers(dest="cmd", required=True)
s = sp.add_parser("tts"); s.add_argument("text", nargs="?"); s.add_argument("--text-file")
s.add_argument("--voice", required=True); s.add_argument("--speed", type=float, default=1.0); s.add_argument("-o", "--out", required=True)
s.set_defaults(fn=cmd_tts)
s = sp.add_parser("sfx"); s.add_argument("prompt"); s.add_argument("--seconds", type=float)
s.add_argument("--influence", type=float, default=0.3); s.add_argument("--loop", action="store_true"); s.add_argument("-o", "--out", required=True)
s.set_defaults(fn=cmd_sfx)
s = sp.add_parser("music"); s.add_argument("prompt"); s.add_argument("--instrumental", action="store_true"); s.add_argument("-o", "--out", required=True)
s.set_defaults(fn=cmd_music)
s = sp.add_parser("image"); s.add_argument("prompt"); s.add_argument("--model", default="bytedance-seedream-4.5")
s.add_argument("--aspect", default="16:9"); s.add_argument("--resolution", default="2K"); s.add_argument("-o", "--out", required=True)
s.set_defaults(fn=cmd_image)
sp.add_parser("credits").set_defaults(fn=cmd_credits)
s = sp.add_parser("voices"); s.add_argument("query", nargs="?", default=""); s.add_argument("--provider", default="elevenlabs")
s.set_defaults(fn=cmd_voices)
s = sp.add_parser("clean"); s.add_argument("--yes", action="store_true"); s.add_argument("--since", default=CLEAN_SINCE)
s.set_defaults(fn=cmd_clean)
a = p.parse_args(); a.fn(a)
