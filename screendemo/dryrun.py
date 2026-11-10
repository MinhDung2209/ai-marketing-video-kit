"""screendemo/dryrun.py — Shot dry-run verification for screendemo videos.

Replays shots.json steps WITHOUT recording (no ffmpeg, no screencast),
asserting:
1. Every target resolves to exactly one visible element at that point.
2. Every mark target (focus/ink text) exists and is visible on the page.
3. No forbidden destructive actions are clicked.

Output format contract:
{
  "ok": bool,
  "errors": [
    {
      "check": "selector",
      "where": "s3 step 4",
      "msg": "...",
      "fix_hint": "..."
    }
  ]
}
Exit 0 if ok, 1 if errors (same format as tools/vqa).
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

# Import shoot helpers
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import shoot


def ensure_cdp_chrome(cdp="9350"):
    """Checks if CDP is already listening. If not and port is 9350, launches Chrome with video-rec-disc profile."""
    cdp_str = str(cdp).strip()
    port = cdp_str if cdp_str.isdigit() else "9350"
    cdp_url = f"http://127.0.0.1:{port}" if cdp_str.isdigit() else cdp_str
    if not cdp_url.startswith("http"):
        cdp_url = f"http://{cdp_url}"

    try:
        with urllib.request.urlopen(f"{cdp_url}/json/version", timeout=1.5) as r:
            return None, cdp_url
    except Exception:
        pass

    chrome_exe = "D:/Apps/Google/Chrome/Application/chrome.exe"
    profile_dir = "D:/chrome-profiles/video-rec-disc"
    if pathlib.Path(chrome_exe).exists():
        proc = subprocess.Popen([
            chrome_exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--window-size=1440,900",
            "--no-first-run",
            "https://tools.stradevn.com",
        ])
        for _ in range(25):
            time.sleep(0.4)
            try:
                with urllib.request.urlopen(f"{cdp_url}/json/version", timeout=1.5) as r:
                    return proc, cdp_url
            except Exception:
                pass
    return None, cdp_url


def get_base_locator(page, target):
    """Resolves target to its base Playwright locator without taking .first or .nth(0)."""
    if isinstance(target, str):
        return page.locator(target)
    root = page
    if target.get("frame"):
        root = next((f for f in page.frames if target["frame"] in f.url), page)
    if "role" in target:
        return root.get_by_role(target["role"], name=target.get("name"), exact=target.get("exact", False))
    elif "after_label" in target:
        ex = root.get_by_text(target["after_label"], exact=True)
        lab = ex.first if ex.count() else root.get_by_text(target["after_label"], exact=False).first
        return lab.locator("xpath=following::input[1]")
    elif "text" in target and "css" not in target:
        return root.get_by_text(target["text"], exact=target.get("exact", False))
    else:
        l = root.locator(target["css"])
        if target.get("has_text"):
            l = l.filter(has_text=target["has_text"])
        return l


def count_visible_locator(loc) -> int:
    """Counts visible elements matching a locator."""
    try:
        cnt = loc.count()
        if cnt == 0:
            return 0
        vis = 0
        for i in range(cnt):
            if loc.nth(i).is_visible():
                vis += 1
        return vis
    except Exception:
        return 0


def check_mark_text_exists(page, text: str, scope: str = "body") -> bool:
    """Verifies that the target text exists and is visible in DOM (TreeWalker / innerText)."""
    try:
        return page.evaluate("""([text, scope]) => {
            const root = document.querySelector(scope) || document.body;
            const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n => {
                const el = n.parentElement; if (!el || el.closest('script,style,noscript,head')) return NodeFilter.FILTER_REJECT;
                const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || !el.getClientRects().length) return NodeFilter.FILTER_REJECT;
                return n.data.includes(text) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
            }});
            if (w.nextNode()) return true;
            const norm = x => x.replace(/\\s+/g, ' ');
            const all = [...root.querySelectorAll('*')].filter(e => e.getClientRects().length && !e.closest('script,style') && norm(e.innerText || '').includes(text));
            return all.length > 0;
        }""", [text, scope])
    except Exception:
        return False


class DryrunSession:
    """Lightweight session mimicking rec.Session for dry running without recording."""
    def __init__(self, page, width=1080, height=1350):
        self.page = page
        self.w = width
        self.h = height
        self.marks = []

    def sleep(self, sec):
        if sec > 0:
            self.page.wait_for_timeout(int(min(sec, 0.5) * 1000))

    def wait(self, a=0.3, b=None):
        self.sleep(a)

    def goto(self, url, wait="domcontentloaded"):
        self.page.goto(url, wait_until=wait)
        self.wait(0.5)

    def settle(self, timeout=6):
        try:
            self.page.wait_for_load_state("load", timeout=timeout * 1000)
        except Exception:
            pass
        self.wait(0.5)

    def start(self):
        pass

    def stop(self):
        pass

    def mark(self, name, **info):
        self.marks.append({"name": name, **info})

    def snap(self, name):
        pass

    def hide_ads(self):
        pass

    def loc(self, target, nth=0):
        return (self.page.locator(target) if isinstance(target, str) else target).nth(nth)

    def click(self, target, nth=0, think=None):
        l = self.loc(target, nth)
        l.click()
        self.wait(0.3)

    def hover(self, target, nth=0):
        l = self.loc(target, nth)
        l.hover()
        self.wait(0.2)

    def type(self, text, cps=None):
        self.page.keyboard.type(text)
        self.wait(0.1)

    def press(self, key):
        self.page.keyboard.press(key)
        self.wait(0.2)

    def scroll(self, dy, dur=0.5):
        self.page.mouse.wheel(0, dy)
        self.wait(0.2)

    def scroll_to(self, target, nth=0, frac=0.35, dur=0.5):
        l = self.loc(target, nth)
        l.scroll_into_view_if_needed()
        self.wait(0.2)

    def focus(self, text, scope="body", name=None, scroll=True, hold=1.0):
        return check_mark_text_exists(self.page, text, scope)

    def mark_text(self, text, scope="body", name=None, scroll=True, color=None, ring=None, hold=1.4):
        return check_mark_text_exists(self.page, text, scope)


def dryrun_clip(clip_dir: str, shots_to_run=None, cdp: str = "9350", json_only: bool = False, page=None):
    """Replays shots.json steps and asserts every target is unique and every mark exists."""
    clip = pathlib.Path(clip_dir).resolve()
    shots_file = clip / "shots.json"
    if not shots_file.exists():
        err = {"ok": False, "errors": [{"check": "file", "where": str(clip), "msg": "shots.json not found", "fix_hint": "Check clip directory path"}]}
        if json_only:
            print(json.dumps(err, ensure_ascii=False, indent=2))
        return err

    S = json.loads(shots_file.read_text(encoding="utf-8"))
    clip_json = clip / "clip.json"
    C = json.loads(clip_json.read_text(encoding="utf-8")) if clip_json.exists() else {}
    V = {**S.get("vars", {}), **C.get("vars", {})}

    prof, mod = shoot.load_profile(S.get("profile") or C.get("profile") or "_none")
    V = {**prof.get("vars", {}), **V}
    w, h = S.get("viewport", [1080, 1350])

    errors = []
    active_shots = shots_to_run if shots_to_run else list(S.get("shots", {}).keys())

    chrome_proc = None
    should_close_pw = False
    pw = None

    if page is None:
        pw = sync_playwright().start()
        should_close_pw = True
        chrome_proc, cdp_url = ensure_cdp_chrome(cdp)

        try:
            browser = pw.chromium.connect_over_cdp(cdp_url)
            ctx = browser.contexts[0]
            page = ctx.new_page()
        except Exception as e:
            chrome_exe = "D:/Apps/Google/Chrome/Application/chrome.exe"
            if pathlib.Path(chrome_exe).exists():
                browser = pw.chromium.launch(executable_path=chrome_exe, headless=True)
                ctx = browser.new_context(viewport={"width": w, "height": h})
                page = ctx.new_page()
            else:
                errors.append({
                    "check": "cdp",
                    "where": "connection",
                    "msg": f"Failed to connect to CDP: {e}",
                    "fix_hint": f"Start Chrome on port {cdp} first",
                })
                res = {"ok": False, "errors": errors}
                if json_only:
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                return res

    try:
        page.set_viewport_size({"width": w, "height": h})
        session = DryrunSession(page, width=w, height=h)
        runner = shoot.Runner(session, prof, mod, V)

        for sid in active_shots:
            if sid not in S.get("shots", {}):
                errors.append({
                    "check": "shot",
                    "where": sid,
                    "msg": f"Shot {sid} not found in shots.json",
                    "fix_hint": "Check shot ID in shots.json",
                })
                continue

            sh = S["shots"][sid]
            miss = shoot.missing_vars(sh.get("steps", []), V)
            if miss:
                errors.append({
                    "check": "vars",
                    "where": sid,
                    "msg": f"Missing variables: {', '.join(sorted(miss))}",
                    "fix_hint": "Define missing variables in clip.json vars",
                })
                continue

            steps = shoot.subst(sh.get("steps", []), V)

            for n, st in enumerate(steps):
                where_id = f"{sid} step {n}"
                if "when" in st and str(st["when"]) not in ("1", "true", "True"):
                    continue

                do = st.get("do", "")

                # 1. Check mark targets for focus and ink
                if do in ("focus", "ink"):
                    mark_text = st.get("text", "")
                    scope = st.get("scope", "body")
                    if not check_mark_text_exists(page, mark_text, scope):
                        errors.append({
                            "check": "selector",
                            "where": where_id,
                            "msg": f"Mark text {mark_text!r} not found or not visible on page (scope={scope!r})",
                            "fix_hint": "Verify text is present in DOM or ensure previous steps navigated/scrolled to it",
                        })

                # 2. Check targets for interactive steps
                target = st.get("target")
                if target is not None:
                    base_loc = get_base_locator(page, target)
                    vis_cnt = count_visible_locator(base_loc)
                    is_disambiguated = isinstance(target, dict) and ("nth" in target or target.get("last"))

                    if vis_cnt == 0:
                        errors.append({
                            "check": "selector",
                            "where": where_id,
                            "msg": f"Target {target} resolved to 0 visible elements",
                            "fix_hint": "Verify selector/text matches current page content and element is not hidden",
                        })
                    elif vis_cnt > 1 and not is_disambiguated:
                        errors.append({
                            "check": "selector",
                            "where": where_id,
                            "msg": f"Target {target} resolved to {vis_cnt} visible elements (ambiguous)",
                            "fix_hint": "Disambiguate with role+name, container, or exact text",
                        })

                # 3. Check safety on click
                if do == "click" and target is not None:
                    loc = runner.loc(target)
                    try:
                        txt = (loc.inner_text(timeout=2000) or "").strip().lower()
                    except Exception:
                        txt = ""
                    for bad in runner.never:
                        if bad and bad in txt:
                            errors.append({
                                "check": "selector",
                                "where": where_id,
                                "msg": f"Forbidden button clicked: {txt!r} (safety.never_click)",
                                "fix_hint": "Do not click forbidden action buttons",
                            })

                # 4. Execute step to advance the page state
                try:
                    f = getattr(runner, "do_" + do, None)
                    args = {k: v for k, v in st.items() if k not in ("do", "when", "note")}
                    if f:
                        f(**args)
                    elif mod and hasattr(mod, do):
                        getattr(mod, do)(runner, **args)
                except Exception:
                    pass

    finally:
        if should_close_pw:
            try:
                page.close()
            except Exception:
                pass
            try:
                pw.stop()
            except Exception:
                pass
        if chrome_proc:
            try:
                chrome_proc.terminate()
                chrome_proc.wait(timeout=3)
            except Exception:
                pass

    res = {
        "ok": len(errors) == 0,
        "errors": errors,
    }

    if json_only:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        status_str = "PASSED" if res["ok"] else f"FAILED with {len(errors)} errors"
        print(f"=== Dry Run {status_str} ===")
        print(json.dumps(res, ensure_ascii=False, indent=2))

    return res


def main():
    parser = argparse.ArgumentParser(description="Dry-run verification of shots.json steps.")
    parser.add_argument("clip_dir", help="Path to clip directory containing shots.json")
    parser.add_argument("shots", nargs="*", help="Optional shot IDs to dry run (default: all)")
    parser.add_argument("--cdp", default="9350", help="CDP port or URL (default: 9350)")
    parser.add_argument("--json", action="store_true", help="Output JSON only to stdout")
    args = parser.parse_args()

    result = dryrun_clip(
        clip_dir=args.clip_dir,
        shots_to_run=args.shots if args.shots else None,
        cdp=args.cdp,
        json_only=args.json,
    )

    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
