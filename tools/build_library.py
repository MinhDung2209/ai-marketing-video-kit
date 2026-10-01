"""Gom thư viện âm thanh SẠCH GIẤY PHÉP từ các repo đã clone (_repos/) → kit/audio-library/ + catalog.json.

Chỉ nhận file có giấy phép dùng thương mại rõ ràng, ghi nguồn + giấy phép TỪNG FILE:
- hyperframes/skills/media-use/audio/assets/sfx  → Pixabay Content License (19 SFX)
- video-shotcraft/assets/audio/sfx|bgm           → CHỈ file có URL Mixkit trong ATTRIBUTION.md (bỏ file "无法反查")
- uisfx/packages/uisfx/sounds                    → CC0 1.0 (936 SFX, 12 bộ phong cách)
KHÔNG gom: soundcn (110 âm thanh © Blizzard All Rights Reserved lẫn trong đó; âm thanh nhúng trong .ts).

Dùng: python kit/tools/build_library.py [--repos _repos] [--out kit/audio-library]
"""
import sys as _sys
try: _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass   # cửa sổ lệnh Windows mặc định không in được tiếng Việt
import argparse, json, re, shutil, subprocess, pathlib

ap = argparse.ArgumentParser()
ap.add_argument("--repos", default="_repos"); ap.add_argument("--out", default="kit/audio-library")
a = ap.parse_args()
R, OUT = pathlib.Path(a.repos), pathlib.Path(a.out)
catalog = []

def dur(p):
    try:
        return round(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                    "-of", "csv=p=0", str(p)]).decode().strip()), 2)
    except Exception:
        return None

def add(src, rel, kind, source, license_, note=""):
    dst = OUT / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
    catalog.append({"id": rel.rsplit(".", 1)[0].replace("/", "."), "path": rel, "kind": kind, "source": source,
                    "license": license_, "duration": dur(dst), "note": note})

# 1) HyperFrames — Pixabay
hf = R / "hyperframes/skills/media-use/audio/assets/sfx"
man = {}
if (hf / "manifest.json").exists():
    m = json.load(open(hf / "manifest.json", encoding="utf-8"))
    for it in (m if isinstance(m, list) else m.get("sounds", m.get("files", []))):
        if isinstance(it, dict) and it.get("file"): man[it["file"]] = it
for f in sorted(hf.glob("*.mp3")):
    note = json.dumps(man.get(f.name, {}), ensure_ascii=False)[:200] if f.name in man else ""
    add(f, f"sfx/pixabay/{f.name}", "sfx", "hyperframes (Pixabay)", "Pixabay Content License", note)

# 2) video-shotcraft — chỉ file có URL Mixkit
sc = R / "video-shotcraft/assets/audio"; att = (sc / "ATTRIBUTION.md").read_text(encoding="utf-8")
for line in att.splitlines():
    cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
    if len(cells) < 3: continue
    url = next((c for c in cells if "mixkit.co" in c and c.startswith("http")), None)
    m = re.search(r"https://\S+", " ".join(cells))
    if not url and m and "mixkit.co" in m.group(0): url = m.group(0)
    if not url: continue
    name = cells[0]
    if name.endswith(".mp3"):
        folder = next((c for c in cells if c.startswith("sfx/")), None)
        if folder:
            src = sc / folder / name
            if src.exists(): add(src, f"sfx/mixkit/{folder[4:].strip('/')}/{name}", "sfx", "video-shotcraft (Mixkit)", "Mixkit Sound Effects Free License", url)
        elif (sc / "bgm" / name).exists():
            add(sc / "bgm" / name, f"bgm/mixkit/{name}", "bgm", "video-shotcraft (Mixkit)", "Mixkit Stock Music Free License", url)

# 3) uisfx — CC0
us = R / "uisfx/packages/uisfx/sounds"
for f in sorted(us.glob("*/*.mp3")):
    add(f, f"sfx/uisfx/{f.parent.name}/{f.name}", "sfx", "uisfx", "CC0 1.0")

json.dump(catalog, open(OUT / "catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
by = {}
for c in catalog: by[c["source"]] = by.get(c["source"], 0) + 1
print("tổng", len(catalog), by)
