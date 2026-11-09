"""Quay màn hình theo kịch bản thao tác DẠNG DỮ LIỆU (shots.json trong thư mục clip) — không phải viết code cho mỗi clip.

  python KIT/screendemo/shoot.py <clip> --list                 # liệt kê cảnh quay + kiểm biến còn thiếu
  python KIT/screendemo/shoot.py <clip> h2 h7                   # quay cảnh h2, h7 → assets/screen/<id>/ (+ sheet.jpg để soát)
  python KIT/screendemo/shoot.py <clip> h5 --set CREATE=1       # bật biến (vd cho phép bấm nút "Tạo" thật)

Trước khi quay: mở "Chrome quay video" (profile riêng, cổng debug) và NGƯỜI DÙNG tự đăng nhập web cần quay.
Bản quay cũ được chuyển sang assets/screen/_old/ chứ không bị ghi đè mất.

shots.json:
  {"profile": "stradevn",                       ← KIT/profiles/<tên>/: luật an toàn + thao tác riêng (actions.py)
   "viewport": [720, 1080],
   "shots": {"h2": {"note": "…", "steps": [ {"do": "goto", "url": "https://…"}, {"do": "start"}, … ]}}}
Biến: "${ten}" lấy từ clip.json → "vars" (và --set). Mọi bước xem ACTIONS bên dưới; docs: KIT/docs/12.
"""
import argparse, datetime, importlib.util, json, pathlib, re, shutil, subprocess, sys
HERE = pathlib.Path(__file__).resolve().parent; KIT = HERE.parent
sys.path.insert(0, str(HERE))
VAR = re.compile(r"\$\{(\w+)\}")


def subst(x, V):
    if isinstance(x, str):
        def r(m):
            if m.group(1) not in V: raise KeyError(m.group(1))
            v = V[m.group(1)]; return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
        if VAR.fullmatch(x) and VAR.fullmatch(x).group(1) in V and not isinstance(V[VAR.fullmatch(x).group(1)], str):
            return V[VAR.fullmatch(x).group(1)]                     # "${list}" → giữ nguyên kiểu (list, số…)
        return VAR.sub(r, x)
    if isinstance(x, list): return [subst(y, V) for y in x]
    if isinstance(x, dict): return {k: subst(v, V) for k, v in x.items()}
    return x


def missing_vars(x, V, acc=None):
    acc = set() if acc is None else acc
    if isinstance(x, str): acc.update(n for n in VAR.findall(x) if n not in V or str(V[n]).startswith("ĐIỀN"))
    elif isinstance(x, list): [missing_vars(y, V, acc) for y in x]
    elif isinstance(x, dict): [missing_vars(y, V, acc) for y in x.values()]
    return acc


def load_profile(name):
    d = KIT / "profiles" / name
    prof = json.loads((d / "profile.json").read_text(encoding="utf-8")) if (d / "profile.json").exists() else {}
    mod = None
    if (d / "actions.py").exists():
        spec = importlib.util.spec_from_file_location(f"profile_{name}", d / "actions.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return prof, mod


class Runner:
    """Chạy từng bước trên 1 rec.Session; chặn nút cấm theo profile."""
    def __init__(self, s, prof, mod, V):
        self.s, self.prof, self.mod, self.V = s, prof, mod, V
        self.never = [t.lower() for t in prof.get("safety", {}).get("never_click", [])]
        self.guard = {k.lower(): v for k, v in prof.get("safety", {}).get("needs_var", {}).items()}

    def loc(self, t):
        """target: "css" | {"css", "has_text", "nth", "last"} | {"text", "exact"} | {"role", "name", "exact"} |
        {"after_label": "Nhãn"} (ô input đầu tiên sau nhãn) | {"frame": "một phần URL iframe", …}"""
        p = self.s.page
        if isinstance(t, str): return p.locator(t).first
        root = p
        if t.get("frame"): root = next(f for f in p.frames if t["frame"] in f.url)
        if "role" in t: l = root.get_by_role(t["role"], name=t.get("name"), exact=t.get("exact", False))
        elif "after_label" in t:   # khớp NGUYÊN nhãn trước ("Từ khóa Tiềm năng" ≠ "Từ khóa Tiềm năng cao (…)"), không có mới khớp một phần
            ex = root.get_by_text(t["after_label"], exact=True)
            lab = ex.first if ex.count() else root.get_by_text(t["after_label"], exact=False).first
            l = lab.locator("xpath=following::input[1]")
        elif "text" in t and "css" not in t: l = root.get_by_text(t["text"], exact=t.get("exact", False))
        else:
            l = root.locator(t["css"])
            if t.get("has_text"): l = l.filter(has_text=t["has_text"])
        return l.last if t.get("last") else l.nth(t.get("nth", 0))

    def check_click(self, l):
        try: txt = (l.inner_text(timeout=3000) or "").strip().lower()
        except Exception: txt = ""
        for bad in self.never:
            if bad and bad in txt: raise SystemExit(f"⛔ chặn bấm {txt!r} — nút cấm theo profile (safety.never_click)")
        for k, var in self.guard.items():
            if k in txt and str(self.V.get(var, "")) not in ("1", "true", "True"):
                raise SystemExit(f"⛔ nút {txt!r} cần bật biến {var}=1 (--set {var}=1) — việc thật, phải được người dùng duyệt")

    def run(self, steps):
        for n, st in enumerate(steps):
            if "when" in st and str(st["when"]) not in ("1", "true", "True"): continue
            do = st["do"]; f = getattr(self, "do_" + do, None)
            args = {k: v for k, v in st.items() if k not in ("do", "when", "note")}
            try:
                if f: f(**args)
                elif self.mod and hasattr(self.mod, do): getattr(self.mod, do)(self, **args)
                else: raise SystemExit(f"bước {n}: không có thao tác {do!r} (kit hay profile)")
            except SystemExit: raise
            except Exception as e:
                raise SystemExit(f"❌ hỏng ở bước {n} {json.dumps(st, ensure_ascii=False)[:160]}\n   {type(e).__name__}: {str(e)[:300]}")

    # ---------- thao tác chung
    def do_goto(self, url, settle=True):
        self.s.goto(url)
        if settle: self.s.settle()
    def do_settle(self): self.s.settle()
    def do_start(self): self.s.start()
    def do_wait(self, sec=0.6): self.s.wait(sec)
    def do_mark(self, name, **info): self.s.mark(name, **info)
    def do_snap(self, name): self.s.snap(name)
    def do_hide_ads(self): self.s.hide_ads()
    def do_dismiss_dialogs(self): self.s.page.on("dialog", lambda d: d.dismiss())
    def do_click(self, target, wait=0.0):
        l = self.loc(target); self.check_click(l); self.s.click(l)
        if wait: self.s.wait(wait)
    def do_hover(self, target, wait=0.6): self.s.hover(self.loc(target)); self.s.wait(wait)
    def do_type(self, text, cps=None, clear=False, enter=False):
        if clear: self.s.page.keyboard.press("Control+A")
        self.s.type(text, **({"cps": tuple(cps)} if cps else {}))
        if enter: self.s.press("Enter")
    def do_press(self, key): self.s.press(key)
    def do_key(self, key): self.s.page.keyboard.press(key)
    def do_fill(self, target, text, click=True):
        l = self.loc(target)
        if click: self.s.click(l)
        l.fill(text)
    def do_select(self, target, label, click=True):
        l = self.loc(target)
        if click: self.s.click(l)
        l.select_option(label=label)
    def do_scroll(self, dy, dur=1.0): self.s.scroll(dy, dur)
    def do_scroll_to(self, target, frac=0.35, dur=1.2): self.s.scroll_to(self.loc(target), frac=frac, dur=dur)
    def do_top(self): self.s.page.evaluate("window.scrollTo(0,0)")
    def do_eval(self, js): self.s.page.evaluate(js)
    def do_focus(self, text, name, scope="body", scroll=True, hold=1.0):
        """Camera phóng vào cụm chữ, KHÔNG vẽ (dùng cho hầu hết các ý)."""
        self.s.focus(text, scope=scope, name=name, scroll=scroll, hold=hold)
    def do_ink(self, text, name, scope="body", scroll=True, hold=1.4):
        """Tô + khoanh đỏ đúng cụm chữ. CHỈ 1–2 lần/cảnh, đúng con số lời đọc nhấn (luật "không spam mark")."""
        self.s.mark_text(text, scope=scope, name=name, scroll=scroll, hold=hold)
    def do_pills(self, label, words):
        """Ô nhập dạng thẻ: bấm ô sau nhãn `label`, gõ từng từ + Enter."""
        inp = self.loc({"after_label": label}); self.s.scroll_to(inp, frac=0.45, dur=0.7); self.s.click(inp)
        for w in words: self.s.type(w); self.s.press("Enter")
    def do_google(self, query):
        """Tìm Google (đang ở trang Google): xoá ô tìm, gõ như người, Enter."""
        box = "textarea[name=q], input[name=q]"
        self.s.click(box); self.s.page.keyboard.press("Control+A"); self.s.page.keyboard.press("Backspace")
        self.s.type(query); self.s.wait(0.3); self.s.press("Enter"); self.s.page.wait_for_load_state("domcontentloaded"); self.s.wait(1.6)
    def do_open_result(self, href, name):
        """Bấm kết quả Google có link chứa `href` (phải có sẵn trong trang kết quả — không có thì báo lỗi để đổi từ khoá)."""
        a = self.s.page.locator(f'a[href*="{href}"]:has(h3)').first
        if not a.count(): raise RuntimeError(f"Google không trả bài {href} — đổi từ khoá tìm hoặc bài khác")
        self.s.scroll_to(a, frac=0.45, dur=0.8); self.s.hover(a.locator("h3")); self.s.wait(0.5); self.s.mark(f"chon:{name}")
        self.s.click(a.locator("h3")); self.s.settle(); self.s.hide_ads(); self.s.wait(0.8); self.s.mark(f"mo:{name}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("clip"); ap.add_argument("shots", nargs="*")
    ap.add_argument("--list", action="store_true"); ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--no-sheet", action="store_true")
    a = ap.parse_args()
    clip = pathlib.Path(a.clip).resolve()
    S = json.loads((clip / "shots.json").read_text(encoding="utf-8"))
    C = json.loads((clip / "clip.json").read_text(encoding="utf-8")) if (clip / "clip.json").exists() else {}
    V = {**S.get("vars", {}), **C.get("vars", {})}
    for kv in a.set: k, _, v = kv.partition("="); V[k] = v
    prof, mod = load_profile(S.get("profile") or C.get("profile") or "_none")
    V = {**prof.get("vars", {}), **V}
    if a.list or not a.shots:
        for sid, sh in S["shots"].items():
            miss = missing_vars(sh["steps"], V)
            inks = sum(1 for x in sh["steps"] if x.get("do") == "ink")
            print(f"{sid:6s} {len(sh['steps']):3d} bước · {inks} khoanh  {sh.get('note', '')[:70]}" + (f"  ⚠ thiếu biến: {', '.join(sorted(miss))}" if miss else ""))
            if inks > 4: print(f"       ⚠ {inks} lần khoanh — luật: ~1 lần / 10–15 s, chỉ số lời đọc nhấn; còn lại dùng focus")
        return
    from rec import Session
    w, h = S.get("viewport", [720, 1080])
    for sid in a.shots:
        sh = S["shots"][sid]
        miss = missing_vars(sh["steps"], V)
        if miss: raise SystemExit(f"{sid}: thiếu biến {', '.join(sorted(miss))} — điền vào clip.json → vars")
        steps = subst(sh["steps"], V)
        out = clip / "assets" / "screen" / sid
        if (out / "screen.mp4").exists():
            old = clip / "assets" / "screen" / "_old" / f"{sid}-{datetime.datetime.now():%m%d-%H%M%S}"
            old.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(out), str(old)); print(f"  bản cũ → {old}")
        print(f"\n=== quay {sid}: {sh.get('note', '')}")
        with Session(out, width=w, height=h) as s:
            Runner(s, prof, mod, V).run(steps)
        fr = out / "_frames"
        if fr.exists(): shutil.rmtree(fr, ignore_errors=True)
        mk = json.loads((out / "marks.json").read_text(encoding="utf-8"))["marks"]
        inks = [m for m in mk if "box" in m and m.get("ink", True)]; dur = mk[-1]["t"] if mk else 0
        if inks and dur / len(inks) < 10: print(f"  ⚠ {len(inks)} lần khoanh trong {dur:.0f} s — dày quá (luật ~1 lần / 10–15 s)")
        if not a.no_sheet:
            subprocess.run([sys.executable, "-X", "utf8", str(HERE / "sheet.py"), str(out)])
            print(f"  → soát: {out / 'sheet.jpg'} (mỗi ô = khung ngay sau 1 mốc khoanh/phóng)")


if __name__ == "__main__":
    main()
