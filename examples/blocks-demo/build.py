"""Offline visual fixture using real Story.card/place and synthetic voice chunk times.

Run from any directory: python examples/blocks-demo/build.py [--snap]
No TTS, audio, app recording, or Story.finish side effects are needed for this preview.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[1]
sys.path.insert(0, str(KIT / "screendemo"))
from engine import Story
import blocks as B


def story():
    # Explicit synthetic timings, not a fabricated business result. The number below
    # describes the three cards that are actually present in this fixture.
    chunks = [dict(s=.1 + i * 1.8, e=1.25 + i * 1.8, a=i * 1.8,
                   b=(i + 1) * 1.8, text="Cụm lời mẫu", cap="Cụm lời mẫu") for i in range(3)]
    brand = json.loads((KIT / "profiles/stradevn/profile.json").read_text(encoding="utf-8"))["brand"]
    with patch("engine.all_chunks", return_value={"FLOW": chunks, "REHOOK": chunks}):
        return Story(HERE, brand=brand)


def compose(st):
    flow = B.flow_diagram(st, st.P("FLOW", 0, 3),
                          ["Dữ liệu", "Bộ lọc", "Kết quả"], title="TỪ DỮ LIỆU ĐẾN HÀNH ĐỘNG",
                          details=["Chọn đúng đầu vào", "Giữ điều cần thiết", "Sẵn sàng bước tiếp"])
    rehook = B.kinetic_rehook(st, st.P("REHOOK", 0, 3), "3", "NHÌN LẠI LUỒNG VỪA RỒI",
                             "bước rõ ràng", "ĐÚNG\nHƯỚNG")
    return flow, rehook


def build():
    st = story()
    flow, rehook = compose(st)
    assets = HERE / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copy2(KIT / "templates/news-motion/gsap.min.js", assets / "gsap.min.js")
    fonts = ["html,body{width:1080px;height:1920px}"]
    # Disjoint unicode ranges keep Vietnamese marks and Latin glyphs on the same family.
    ranges = {"latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
              "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
              "vietnamese": "U+0102-0103,U+0110-0111,U+0128-0129,U+0168-0169,U+01A0-01A1,U+01AF-01B0,U+0300-0301,U+0303-0304,U+0308-0309,U+0323,U+0329,U+1EA0-1EF9,U+20AB"}
    for subset, urange in ranges.items():
        name = f"BeVietnamPro-800-{subset}.woff2"
        shutil.copy2(KIT / "templates/fonts" / name, assets / name)
        fonts.append(f"@font-face{{font-family:'Be Vietnam Pro';font-style:normal;font-weight:800;"
                     f"src:url('assets/{name}') format('woff2');unicode-range:{urange}}}")
    sections = []
    for n, html in enumerate(st.html):
        sections.append(html.replace('<section ', f'<section id="scene{n}" data-track-index="0" ', 1))
    # Use the kit's template so the result retains the same HyperFrames contract.
    page = (KIT / "screendemo/templates/template.html").read_text(encoding="utf-8")
    page = page.replace("https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js", "assets/gsap.min.js")
    page = page.replace("'IBM Plex Sans'", "'Be Vietnam Pro'")
    page = page.replace('const tl = gsap.timeline', 'const standalonePreview = !window.__timelines;\nconst tl = gsap.timeline')
    for old, new in {"/*FONTS*/": "\n".join(fonts), "__W__": "1080", "__H__": "1920",
                     "__D__": str(st.now), "__HL__": st.brand["hl"], "__ACCENT__": st.brand["accent"],
                     "__CAPTOP__": "1440", "Video marketing": "Khối cảnh · bản xem thử",
                     "__SECTIONS__": "\n".join(sections), "__CAPTIONS__": "",
                     "__JS__": "\n".join(st.js)}.items():
        page = page.replace(old, new)
    page = page.replace('window.__timelines["main"] = tl;',
                        'window.__timelines = window.__timelines || {}; window.__timelines["main"] = tl;')
    # A direct file:// preview can be scrubbed with ?t=9.9 or arrow keys. No clock.
    page = page.replace('</script>\n</body>', '''
function previewAt(t) {
  tl.seek(t, false);
  document.querySelectorAll('section[data-start]').forEach(el => {
    const s = +el.dataset.start, d = +el.dataset.duration;
    el.style.visibility = t >= s && t < s + d ? 'visible' : 'hidden';
  });
}
if (standalonePreview) {
  let position = Number(new URLSearchParams(location.search).get('t') || 4.8);
  document.fonts.ready.then(() => previewAt(position));
  document.addEventListener('keydown', e => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    position = Math.max(0, Math.min(+document.getElementById('root').dataset.duration - .01,
      position + (e.key === 'ArrowRight' ? .1 : -.1)));
    previewAt(position);
  });
}
</script>\n</body>''')
    (HERE / "index.html").write_text(page, encoding="utf-8")
    times = [round(flow[1] - .15, 1), round(flow[2] + .6, 1),
             round(rehook[2] + .15, 1), round(rehook[2] + .75, 1)]
    (HERE / "cues.json").write_text(json.dumps(dict(flow=flow, rehook=rehook, snapshots=times,
                                                   duration=st.now), indent=2), encoding="utf-8")
    print(f"Built index.html: {st.now:.2f}s; flow={flow}; rehook={rehook}")
    return times


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snap", action="store_true", help="Use tools/render.py and copy four PNGs to K02 report")
    args = ap.parse_args()
    times = build()
    if args.snap:
        env = os.environ.copy()
        chrome = Path("D:/Apps/Google/Chrome/Application/chrome.exe")
        if chrome.exists():
            env.setdefault("VIDEOKIT_CHROME", str(chrome))
        subprocess.run([sys.executable, str(KIT / "tools/render.py"), str(HERE),
                        "--snap", ",".join(map(str, times))], env=env, check=True)
        report = KIT / "orchestration/reports/K02"
        report.mkdir(parents=True, exist_ok=True)
        for label, t in zip(("flow-drawing", "flow-complete", "rehook-wipe", "rehook-hold"), times):
            shutil.copy2(HERE / f"_snap_{t:05.1f}.png", report / f"{label}.png")
        print("Copied four PNG snapshots to orchestration/reports/K02/")


if __name__ == "__main__":
    main()
