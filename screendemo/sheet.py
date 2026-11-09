"""Ghép khung hình ngay sau mỗi mốc → sheet.jpg để soát bằng mắt.
python sheet.py <thư mục bản quay> [giây sau mốc] [all]   (mặc định chỉ mốc có khoanh; 'all' = mọi mốc)"""
import json, shutil, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from rec import FFMPEG as F
d =pathlib.Path(sys.argv[1]).resolve()
dt = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0; every = "all" in sys.argv[3:]
m = [x for x in json.load(open(d / "marks.json", encoding="utf-8"))["marks"] if every or "box" in x]
font = "fontfile='C\\:/Windows/Fonts/arial.ttf'"
fs = []
for i, x in enumerate(m):
    f = d / f"_s{i}.jpg"
    subprocess.run([F, "-y", "-loglevel", "error", "-ss", str(x["t"] + dt), "-i", str(d / "screen.mp4"), "-frames:v", "1",
                    "-vf", f"scale=240:-1,drawtext={font}:text='{x['name'].replace(':', '-')}':x=6:y=6:fontsize=16:fontcolor=red:box=1:boxcolor=white", str(f)])
    if f.exists(): fs.append(f)
out = d / "sheet.jpg"
if len(fs) == 1: shutil.copy(fs[0], out)
elif fs:
    cols = 7
    args = [a for f in fs for a in ("-i", str(f))]
    lay = "|".join((("+".join(["w0"] * (i % cols))) or "0") + "_" + (("+".join(["h0"] * (i // cols))) or "0") for i in range(len(fs)))
    subprocess.run([F, "-y", "-loglevel", "error", *args, "-filter_complex",
                    "".join(f"[{i}]" for i in range(len(fs))) + f"xstack=inputs={len(fs)}:layout={lay}:fill=white", str(out)])
for f in fs: f.unlink(missing_ok=True)
print(out, len(fs), "ảnh")
