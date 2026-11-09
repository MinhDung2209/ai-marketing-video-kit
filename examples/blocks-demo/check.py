"""Regression checks for cue timing, repeated blocks and random-access rendering."""
import os
import re
import sys
import unittest
import unicodedata

from build import B, HERE, KIT, compose, story

sys.path.insert(0, str(KIT / "tools"))
from render import SEEK_JS, find_chrome
from playwright.sync_api import sync_playwright


class BlockContract(unittest.TestCase):
    def test_repeated_blocks_have_unique_ids_and_absolute_times(self):
        st = story()
        first = compose(st)
        second = compose(st)
        ids = re.findall(r'\bid="([^"]+)"', "".join(st.html))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(second[0][0], first[1][-1])
        self.assertIn(f"{second[1][1]:.3f});", "\n".join(st.js))
        for js in st.js:
            self.assertNotRegex(js, r"Date\.now|performance\.now|Math\.random|setInterval|requestAnimationFrame")
            self.assertIn("immediateRender:false", js)

    def test_cues_can_select_later_chunks(self):
        st = story()
        st.CH["FLOW"].append(dict(s=5.5, e=6.65, a=5.4, b=7.2, text="Cuối", cap="Cuối"))
        starts = B.flow_diagram(st, st.P("FLOW", 0, 4), ["A", "B", "C"], cues=(0, 2, 3))
        self.assertIn(f"{starts[2]:.3f});", st.js[2])
        self.assertEqual(len(starts), 4)

    def test_invalid_contracts_fail_before_story_mutation(self):
        st = story()
        for cues in ((0, 0, 2), (0, 1, 3), (-1, 1, 2)):
            with self.assertRaises(ValueError):
                B.flow_diagram(st, st.P("FLOW", 0, 3), ["A", "B", "C"], cues=cues)
        with self.assertRaises(ValueError):
            B.flow_diagram(st, st.P("FLOW", 0, 3), ["A", "B"])
        for value, payoff in (("12/20", "Đúng"), ("NaN", "Đúng"), ("12", "Thêm 2")):
            with self.assertRaises(ValueError):
                B.kinetic_rehook(st, st.P("REHOOK", 0, 3), value, "Nhìn lại", "email", payoff)
        st.brand = {}
        with self.assertRaises(ValueError):
            B.flow_diagram(st, st.P("FLOW", 0, 3), ["A", "B", "C"])
        self.assertEqual(st.html, [])
        self.assertEqual(st.now, 0)

    def test_profile_colors_plain_text_and_vietnamese(self):
        st = story()
        st.brand = dict(hl="#22AA66", accent="#CC4411")
        B.flow_diagram(st, st.P("FLOW", 0, 3),
                       [unicodedata.normalize("NFD", "Dữ liệu"), "<script>x</script>", "A & B"])
        html = st.html[0]
        self.assertIn("Dữ liệu", html)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", html)
        self.assertIn("A &amp; B", html)
        self.assertIn("--hl:#22AA66;--accent:#CC4411", html)
        B.kinetic_rehook(st, st.P("REHOOK", 0, 3), "17,8", "Nhìn lại", "%", "Đúng hướng")
        self.assertEqual(st.html[-1].count("17,8"), 1)


class BrowserContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        chrome = "D:/Apps/Google/Chrome/Application/chrome.exe"
        if os.path.exists(chrome):
            os.environ.setdefault("VIDEOKIT_CHROME", chrome)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(executable_path=find_chrome(), headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def page(self):
        page = self.browser.new_page(viewport=dict(width=1080, height=1920))
        page.add_init_script("window.__timelines = {}")
        page.goto((HERE / "index.html").as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        return page

    def test_random_access_matches_fresh_frames(self):
        page = self.page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        frames = {}
        for t in (0, .2, .5, 1.9, 2.2, 4.5, 5.7, 6.1, 7.9, 9.7, 9.8, 10.4, 11.54):
            page.evaluate(SEEK_JS, t)
            frames[t] = page.screenshot()
        for t in reversed(frames):
            page.evaluate(SEEK_JS, t)
            self.assertEqual(page.screenshot(), frames[t], f"backward seek changed frame {t}")
        # Each isolated seek has the same result as sequential and reverse seeking.
        for t in (1.9, 4.5, 9.8, 10.4):
            fresh = self.page()
            fresh.evaluate(SEEK_JS, t)
            self.assertEqual(fresh.screenshot(), frames[t], f"fresh seek changed frame {t}")
            fresh.close()
        self.assertEqual(errors, [])
        page.close()

    def test_voice_reveals_fonts_and_safe_bounds(self):
        page = self.page()
        for t, count in ((.2, 0), (.9, 1), (2.6, 2), (4.5, 3)):
            page.evaluate(SEEK_JS, t)
            visible = page.locator(".node").evaluate_all("els => els.filter(e => +getComputedStyle(e).opacity > .99).length")
            self.assertEqual(visible, count)
        for t, sid, sizes in ((4.5, "flow0", ["44px", "68px"]), (10.4, "rehook1", ["148px", "44px"])):
            page.evaluate(SEEK_JS, t)
            actual = page.locator(f"#{sid} .copy").evaluate_all("els => [...new Set(els.map(e => getComputedStyle(e).fontSize))].sort()")
            self.assertEqual(actual, sizes)
            boxes = page.locator(f"#{sid} .copy").evaluate_all("els => els.map(e => {const r=e.getBoundingClientRect();return [r.left,r.right,r.bottom,e.scrollWidth,e.clientWidth]})")
            for left, right, bottom, scroll, client in boxes:
                self.assertGreaterEqual(left, 90)
                self.assertLessEqual(right, 910)
                self.assertLess(bottom, 1440)
                self.assertLessEqual(scroll, client)
        # Latin-ext overlaps Vietnamese ranges but may remain unused. First verify
        # the rendered subsets, then explicitly exercise the complete query.
        self.assertTrue(page.evaluate("[...document.fonts].some(f => f.unicodeRange.includes('1EA0') && f.status === 'loaded')"))
        page.evaluate("document.fonts.load('800 148px \"Be Vietnam Pro\"', 'ĐÚNG HƯỚNG Dữ liệu')")
        self.assertTrue(page.evaluate("document.fonts.check('800 148px \"Be Vietnam Pro\"', 'ĐÚNG HƯỚNG Dữ liệu')"))
        page.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
