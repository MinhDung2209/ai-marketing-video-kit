"""screendemo/discover.py — App discovery for screen-demo marketing videos.

Crawls same-origin links, tabs, and navigation reachable by click (read-only navigation only),
and records an inventory of visible interactive elements, targets, and concrete facts so a model
never has to guess selectors or data.

Output format contract:
{
  "base": url,
  "viewport": [w, h],
  "pages": [
    {
      "url": "...",
      "title": "...",
      "screenshot": "screenshots/page_00.png",
      "nav": [...],
      "elements": [
        {
          "kind": "tab|button|link|input|table|number|heading",
          "label": "visible text",
          "target": <shoot.py target dict that resolves to exactly 1 visible element>,
          "box": [x, y, w, h],
          "safe": bool
        }
      ],
      "facts": [
        {
          "text": "24000 KGS",
          "context": "row text / column header",
          "target": ...
        }
      ],
      "text_path": "texts/page_00.txt"
    }
  ]
}
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from playwright.sync_api import sync_playwright

FORBIDDEN_TEXTS = [
    "tạo chiến dịch",
    "bắt đầu truy xuất",
    "gửi",
    "send",
    "xoá",
    "xóa",
    "delete",
    "lưu",
    "thanh toán",
]


def is_safe_action(label: str, tag: str = "", attrs: dict = None) -> bool:
    """Read-only browsing guard: checks if element text or attributes contain forbidden actions."""
    if not label and not tag and not attrs:
        return True
    lbl = (label or "").strip().lower()
    for bad in FORBIDDEN_TEXTS:
        if bad in lbl:
            return False
    if tag == "form":
        return False
    if attrs:
        t = (attrs.get("type") or "").lower()
        if t == "submit":
            return False
        aria = (attrs.get("aria-label") or "").lower()
        for bad in FORBIDDEN_TEXTS:
            if bad in aria:
                return False
    return True


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


def count_visible_target(page, target) -> int:
    """Counts how many visible elements in page match target using shoot.py resolution logic."""
    try:
        if isinstance(target, str):
            loc = page.locator(target)
        elif "role" in target:
            loc = page.get_by_role(target["role"], name=target.get("name"), exact=target.get("exact", False))
        elif "after_label" in target:
            ex = page.get_by_text(target["after_label"], exact=True)
            lab = ex.first if ex.count() else page.get_by_text(target["after_label"], exact=False).first
            loc = lab.locator("xpath=following::input[1]")
        elif "text" in target and "css" not in target:
            loc = page.get_by_text(target["text"], exact=target.get("exact", False))
        else:
            loc = page.locator(target["css"])
            if target.get("has_text"):
                loc = loc.filter(has_text=target["has_text"])

        cnt = loc.count()
        if cnt == 0:
            return 0
        if cnt == 1:
            return 1 if loc.first.is_visible() else 0
        vis = 0
        for i in range(cnt):
            if loc.nth(i).is_visible():
                vis += 1
                if vis > 1:
                    return vis
        return vis
    except Exception:
        return 0


def rank_target_for_element(page, item: dict) -> dict:
    """Finds a shoot.py target dict that resolves to exactly 1 visible element on page.

    Priority:
    1. role + name (exact=True, then exact=False)
    2. text (exact=True, then exact=False)
    3. css (id, data-testid, class+has_text, semantic selector, xpath/nth fallback)
    """
    role = item.get("role")
    name = (item.get("name") or "").strip()
    text = (item.get("text") or "").strip()
    el_id = item.get("id")
    testid = item.get("testid")
    tag = item.get("tag") or ""
    css_path = item.get("css_path") or ""
    after_label = item.get("after_label")

    # 1. Prefer role + name
    if role and name:
        cand1 = {"role": role, "name": name, "exact": True}
        if count_visible_target(page, cand1) == 1:
            return cand1
        cand2 = {"role": role, "name": name, "exact": False}
        if count_visible_target(page, cand2) == 1:
            return cand2

    # 2. Prefer text
    if text and len(text) <= 80:
        cand3 = {"text": text, "exact": True}
        if count_visible_target(page, cand3) == 1:
            return cand3
        cand4 = {"text": text, "exact": False}
        if count_visible_target(page, cand4) == 1:
            return cand4

    # 3. Prefer ID / data-testid
    if el_id:
        cand_id = {"css": f"#{el_id}"}
        if count_visible_target(page, cand_id) == 1:
            return cand_id
    if testid:
        cand_test = {"css": f"[data-testid='{testid}']"}
        if count_visible_target(page, cand_test) == 1:
            return cand_test

    # 4. after_label for inputs
    if after_label:
        cand_after = {"after_label": after_label}
        if count_visible_target(page, cand_after) == 1:
            return cand_after

    # 5. Semantic CSS with has_text
    search_text = name or (text[:40] if text else "")
    if search_text:
        for prefix in (":is(a,button,[role=tab]):visible", f"{tag}:visible", f"{tag}"):
            cand_sem = {"css": prefix, "has_text": search_text}
            if count_visible_target(page, cand_sem) == 1:
                return cand_sem

    # 6. CSS path
    if css_path:
        cand_css = {"css": css_path}
        if count_visible_target(page, cand_css) == 1:
            return cand_css

    # 7. Fallback: unique disambiguation with has_text
    fallback_css = css_path or (f"#{el_id}" if el_id else tag or "*")
    if search_text:
        return {"css": fallback_css, "has_text": search_text}
    return {"css": fallback_css}


JS_EXTRACT_PAGE_DATA = r"""
(() => {
  const isVisible = (el) => {
    if (!el || el.nodeType !== 1) return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    if (el.closest('.mobile-only') && window.innerWidth >= 1024) return false;
    if (el.closest('.sr-only, [aria-hidden="true"]')) return false;
    return true;
  };

  const getCleanText = (el) => {
    if (!el) return '';
    return (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
  };

  const getCssPath = (el) => {
    if (!el || el.nodeType !== 1) return '';
    if (el.id) return `#${el.id}`;
    if (el.getAttribute('data-testid')) return `[data-testid="${el.getAttribute('data-testid')}"]`;
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && cur !== document.body && cur !== document.documentElement) {
      let tag = cur.tagName.toLowerCase();
      if (cur.id) {
        parts.unshift(`#${cur.id}`);
        break;
      }
      let sibIndex = 1;
      let sib = cur.previousElementSibling;
      while (sib) {
        if (sib.tagName === cur.tagName) sibIndex++;
        sib = sib.previousElementSibling;
      }
      parts.unshift(`${tag}:nth-of-type(${sibIndex})`);
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  };

  const elements = [];
  const allNodes = document.querySelectorAll('a, button, input, select, textarea, table, [role], h1, h2, h3, h4, h5, h6, .stat-card, [class*="stat"], [class*="badge"], [class*="chip"]');
  
  for (const el of allNodes) {
    if (!isVisible(el)) continue;
    const tag = el.tagName.toLowerCase();
    const roleAttr = (el.getAttribute('role') || '').toLowerCase();
    const typeAttr = (el.getAttribute('type') || '').toLowerCase();
    let role = roleAttr;
    if (!role) {
      if (tag === 'button' || (tag === 'input' && (typeAttr === 'button' || typeAttr === 'submit'))) role = 'button';
      else if (tag === 'a' && el.hasAttribute('href')) role = 'link';
      else if (tag === 'input' || tag === 'textarea') role = 'textbox';
      else if (tag === 'select') role = 'combobox';
      else if (tag === 'table') role = 'table';
      else if (/^h[1-6]$/.test(tag)) role = 'heading';
    }

    const rect = el.getBoundingClientRect();
    const box = [Math.round(rect.left), Math.round(rect.top), Math.round(rect.width), Math.round(rect.height)];
    const text = getCleanText(el);
    const ariaLabel = (el.getAttribute('aria-label') || '').trim();
    const placeholder = (el.getAttribute('placeholder') || '').trim();
    const name = ariaLabel || (['textbox', 'combobox'].includes(role) ? placeholder : text);

    // Identify kind
    let kind = '';
  const isTab = role === 'tab' ||
                el.classList.contains('navitem') ||
                el.classList.contains('tab') ||
                !!el.closest('aside.sidebar, nav, [role="tablist"], nav.campaign-tabs-mobile, .tabs, .sidebar');
  if (isTab && (role === 'tab' || role === 'button' || role === 'link' || tag === 'button' || tag === 'a')) {
    kind = 'tab';
  } else if (role === 'button' || tag === 'button') {
      kind = 'button';
    } else if (role === 'link' || tag === 'a') {
      kind = 'link';
    } else if (['input', 'textarea', 'select'].includes(tag) || ['textbox', 'combobox', 'searchbox', 'spinbutton'].includes(role)) {
      kind = 'input';
    } else if (tag === 'table' || role === 'table') {
      kind = 'table';
    } else if (/^h[1-6]$/.test(tag) || role === 'heading') {
      kind = 'heading';
    } else if (/\d/.test(text) && (text.length <= 40)) {
      kind = 'number';
    }

    if (!kind) continue;

    // Preceding label for inputs
    let after_label = null;
    if (kind === 'input') {
      let prev = el.previousElementSibling;
      while (prev) {
        if (prev.tagName.toLowerCase() === 'label' || prev.querySelector('label')) {
          after_label = getCleanText(prev);
          break;
        }
        prev = prev.previousElementSibling;
      }
      if (!after_label && el.parentElement) {
        const lab = el.parentElement.querySelector('label');
        if (lab && lab !== el) after_label = getCleanText(lab);
      }
    }

    elements.push({
      kind: kind,
      tag: tag,
      role: role || (kind === 'tab' ? 'tab' : (kind === 'button' ? 'button' : (kind === 'link' ? 'link' : ''))),
      name: name,
      text: text,
      label: ariaLabel || text || placeholder || (el.getAttribute('title') || ''),
      id: el.id || '',
      testid: el.getAttribute('data-testid') || el.getAttribute('data-qa') || '',
      after_label: after_label,
      css_path: getCssPath(el),
      box: box,
      is_tab: isTab
    });
  }

  // Extract facts: table cells, metrics, contact info
  const facts = [];
  const seenFactKeys = new Set();

  // 1. Table cells
  const tables = document.querySelectorAll('table');
  tables.forEach((tbl, tIdx) => {
    if (!isVisible(tbl)) return;
    const headers = [...tbl.querySelectorAll('th')].map(th => getCleanText(th));
    const rows = tbl.querySelectorAll('tr');
    rows.forEach((tr, rIdx) => {
      if (!isVisible(tr)) return;
      const cells = tr.querySelectorAll('td');
      if (!cells.length) return;
      cells.forEach((td, cIdx) => {
        if (!isVisible(td)) return;
        const txt = getCleanText(td);
        if (!txt) return;
        const colHeader = headers[cIdx] || `Cột ${cIdx + 1}`;
        const ctx = `${colHeader} / dòng ${rIdx}`;

        // Whole cell text if clean and concise
        if (txt.length <= 120) {
          const key = `${txt}@@${ctx}`;
          if (!seenFactKeys.has(key)) {
            seenFactKeys.add(key);
            facts.push({
              text: txt,
              context: ctx,
              css: getCssPath(td)
            });
          }
        }

        // Sub-facts: weights, quantities, currencies, or notable entities within longer text
        const weightMatch = txt.match(/\b\d+[\d\.,]*\s*(?:KGS?|KG|TẤN|TONS?|BAGS?)/gi);
        if (weightMatch) {
          weightMatch.forEach(w => {
            const wClean = w.trim();
            const key = `${wClean}@@${ctx}`;
            if (!seenFactKeys.has(key)) {
              seenFactKeys.add(key);
              facts.push({
                text: wClean,
                context: `${colHeader} / dòng ${rIdx}`,
                css: getCssPath(td)
              });
            }
          });
        }

        const currMatch = txt.match(/(?:\$|USD|VND|EUR)\s*[\d\.,]+|[\d\.,]+\s*(?:USD|VND|EUR|\$)/gi);
        if (currMatch) {
          currMatch.forEach(c => {
            const cClean = c.trim();
            const key = `${cClean}@@${ctx}`;
            if (!seenFactKeys.has(key)) {
              seenFactKeys.add(key);
              facts.push({
                text: cClean,
                context: `${colHeader} / dòng ${rIdx}`,
                css: getCssPath(td)
              });
            }
          });
        }
      });
    });
  });

  // 2. Metric numbers / badges / cards outside tables
  const metricNodes = document.querySelectorAll('p, span, div, h2, h3, h4, strong, b');
  const metricPattern = /(\d+[\d\.,]*\s*(?:KGS?|KG|TẤN|TONS?|BAGS?|LẦN|DÒNG|TIỀM NĂNG|DOANH NGHIỆP|CÔNG TY|KHÁCH|USD|VND|ĐỒNG|EUR|TỶ|TRIỆU)|(?:\$|€|£)\s*[\d\.,]+(?:\s*\/\s*\w+)?|\b\d+[\d\.,]*\s*%(?:\s+so\s+với\s+cùng\s+kỳ)?|(?:\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\b)|[\w\.-]+@[\w\.-]+\.\w+|\+\d{9,15}|www\.\S+)/i;
  
  for (const m of metricNodes) {
    if (!isVisible(m)) continue;
    if (m.closest('table')) continue;
    if (m.children.length > 2) continue;
    const txt = getCleanText(m);
    if (!txt || txt.length > 80) continue;
    const match = metricPattern.exec(txt);
    if (match) {
      const matchText = match[0].trim();
      const parentHead = m.closest('section, div, card, .card')?.querySelector('h1, h2, h3, h4, .title, label');
      const ctx = parentHead ? getCleanText(parentHead) : 'Thống kê / Chỉ số';
      const key = `${matchText}@@${ctx}`;
      if (!seenFactKeys.has(key)) {
        seenFactKeys.add(key);
        facts.push({
          text: matchText,
          context: ctx,
          css: getCssPath(m)
        });
      }
    }
  }

  // Extract navigation tabs/links
  const navItems = [];
  const navNodes = document.querySelectorAll('nav a, nav button, [role="tablist"] [role="tab"], nav.campaign-tabs-mobile button, .tabs a, .tabs button');
  for (const n of navNodes) {
    if (!isVisible(n)) continue;
    const txt = getCleanText(n);
    if (!txt) continue;
    const href = n.getAttribute('href');
    navItems.push({
      label: txt,
      tag: n.tagName.toLowerCase(),
      role: (n.getAttribute('role') || 'tab').toLowerCase(),
      name: txt,
      href: href || null,
      id: n.id || '',
      css_path: getCssPath(n)
    });
  }

  return {
    elements: elements,
    facts: facts,
    nav: navItems
  };
})();
"""


def extract_page_data(page):
    """Evaluates JavaScript to extract elements, facts, and navigation from current page."""
    return page.evaluate(JS_EXTRACT_PAGE_DATA)


def discover_site(
    start_url: str,
    out_json_path: str,
    cdp: str = "9350",
    max_pages: int = 25,
    viewport=(1080, 1350),
    browser=None,
    page=None,
):
    """Walks same-origin links, tabs, and nav reachable by click (navigation only, safe list),

    and writes inventory JSON + inventory.md.
    """
    out_file = pathlib.Path(out_json_path).resolve()
    out_dir = out_file.parent
    screenshots_dir = out_dir / "screenshots"
    texts_dir = out_dir / "texts"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    texts_dir.mkdir(parents=True, exist_ok=True)

    w, h = viewport
    parsed_base = urllib.parse.urlparse(start_url)
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    pages_discovered = []
    visited_urls = set()
    queue = [(start_url, "Initial URL")]

    chrome_proc = None
    should_close_browser = False
    pw = None

    if page is None:
        pw = sync_playwright().start()
        should_close_browser = True
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
                raise e

    try:
        page.set_viewport_size({"width": w, "height": h})

        while queue and len(pages_discovered) < max_pages:
            target_url, reason = queue.pop(0)
            norm_url = target_url.split("#")[0]
            if norm_url in visited_urls:
                continue

            try:
                page.goto(target_url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Warning: failed to load {target_url}: {e}", file=sys.stderr)
                continue

            actual_url = page.url
            norm_actual = actual_url.split("#")[0]
            if norm_actual in visited_urls and len(pages_discovered) > 0:
                continue
            visited_urls.add(norm_actual)

            page_idx = len(pages_discovered)
            snap_rel = f"screenshots/page_{page_idx:02d}.png"
            snap_path = out_dir / snap_rel
            page.screenshot(path=str(snap_path))

            text_rel = f"texts/page_{page_idx:02d}.txt"
            text_path = out_dir / text_rel
            body_text = page.locator("body").inner_text()
            text_path.write_text(body_text, encoding="utf-8")

            # Extract raw DOM items
            raw_data = extract_page_data(page)

            # Process nav items
            nav_items = []
            for n in raw_data.get("nav", []):
                t = rank_target_for_element(page, n)
                nav_items.append({
                    "label": n["label"],
                    "target": t,
                    "url": n.get("href"),
                })

            # Process elements
            elements = []
            for item in raw_data.get("elements", []):
                safe = is_safe_action(item.get("label", ""), item.get("tag", ""))
                target = rank_target_for_element(page, item)
                elements.append({
                    "kind": item["kind"],
                    "label": item["label"],
                    "target": target,
                    "box": item["box"],
                    "safe": safe,
                })

            # Process facts
            facts = []
            for f in raw_data.get("facts", []):
                f_text = f["text"].strip()
                cand_target = {"text": f_text, "exact": True}
                if count_visible_target(page, cand_target) == 1:
                    target = cand_target
                else:
                    target = {"css": f["css"]}
                facts.append({
                    "text": f_text,
                    "context": f["context"],
                    "target": target,
                })

            page_record = {
                "url": actual_url,
                "title": page.title(),
                "screenshot": snap_rel,
                "nav": nav_items,
                "elements": elements,
                "facts": facts,
                "text_path": text_rel,
            }
            pages_discovered.append(page_record)
            print(f"[{len(pages_discovered)}/{max_pages}] Discovered {actual_url} ({len(elements)} elements, {len(facts)} facts)")

            if len(pages_discovered) >= max_pages:
                break

            # Discover tabs on this page by clicking them safely
            safe_tabs = [el for el in elements if el["kind"] == "tab" and el["safe"]]
            base_page_path = actual_url.split("?")[0]

            for tab_el in safe_tabs:
                if len(pages_discovered) >= max_pages:
                    break
                # Skip home / logo brand links in tab list
                if "StradeVn" in tab_el.get("label", "") or tab_el.get("label") == "AI":
                    continue

                try:
                    if not page.url.split("?")[0].startswith(base_page_path):
                        page.goto(actual_url)
                        page.wait_for_timeout(1500)

                    loc = page.locator(tab_el["target"].get("css", "button"))
                    if "role" in tab_el["target"]:
                        loc = page.get_by_role(tab_el["target"]["role"], name=tab_el["target"].get("name"), exact=tab_el["target"].get("exact", False))
                    elif "text" in tab_el["target"]:
                        loc = page.get_by_text(tab_el["target"]["text"], exact=tab_el["target"].get("exact", False))
                    elif tab_el["target"].get("has_text"):
                        loc = loc.filter(has_text=tab_el["target"]["has_text"])

                    if loc.count() > 0 and loc.first.is_visible():
                        loc.first.click()
                        page.wait_for_timeout(2000)
                        new_url = page.url
                        norm_new = new_url.split("#")[0]

                        # If navigated away from current page section, enqueue it and go back
                        if not norm_new.split("?")[0].startswith(base_page_path):
                            if norm_new not in visited_urls:
                                queue.append((new_url, f"Nav: {tab_el['label']}"))
                            page.goto(actual_url)
                            page.wait_for_timeout(1500)
                            continue

                        state_key = norm_new if norm_new not in visited_urls else f"{norm_new}#{tab_el['label']}"
                        if state_key not in visited_urls:
                            visited_urls.add(state_key)
                            t_idx = len(pages_discovered)
                            t_snap_rel = f"screenshots/page_{t_idx:02d}.png"
                            page.screenshot(path=str(out_dir / t_snap_rel))

                            t_text_rel = f"texts/page_{t_idx:02d}.txt"
                            (out_dir / t_text_rel).write_text(page.locator("body").inner_text(), encoding="utf-8")

                            t_raw = extract_page_data(page)
                            t_nav = [
                                {"label": x["label"], "target": rank_target_for_element(page, x), "url": x.get("href")}
                                for x in t_raw.get("nav", [])
                            ]
                            t_elements = [
                                {
                                    "kind": x["kind"],
                                    "label": x["label"],
                                    "target": rank_target_for_element(page, x),
                                    "box": x["box"],
                                    "safe": is_safe_action(x.get("label", ""), x.get("tag", "")),
                                }
                                for x in t_raw.get("elements", [])
                            ]
                            t_facts = []
                            for f in t_raw.get("facts", []):
                                f_text = f["text"].strip()
                                cand_target = {"text": f_text, "exact": True}
                                target = cand_target if count_visible_target(page, cand_target) == 1 else {"css": f["css"]}
                                t_facts.append({"text": f_text, "context": f["context"], "target": target})

                            recorded_url = new_url if state_key == norm_new else f"{new_url}#{tab_el['label']}"
                            pages_discovered.append({
                                "url": recorded_url,
                                "title": page.title(),
                                "screenshot": t_snap_rel,
                                "nav": t_nav,
                                "elements": t_elements,
                                "facts": t_facts,
                                "text_path": t_text_rel,
                            })
                            print(f"[{len(pages_discovered)}/{max_pages}] Tab view: {tab_el['label']} -> {new_url} ({len(t_elements)} elements, {len(t_facts)} facts)")
                except Exception:
                    continue

            # Discover same-origin links
            for el in raw_data.get("elements", []):
                if el["kind"] == "link" and el.get("href"):
                    href = el["href"]
                    full = urllib.parse.urljoin(actual_url, href)
                    if full.startswith(origin) and full not in visited_urls:
                        if not any(bad in full.lower() for bad in ("logout", "signout", "delete", "destroy")):
                            queue.append((full, f"Link: {el['label']}"))

    finally:
        if should_close_browser:
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

    inventory = {
        "base": start_url,
        "viewport": [w, h],
        "pages": pages_discovered,
    }

    out_file.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n Inventory JSON saved to: {out_file}")

    # Generate human-readable inventory.md
    md_file = out_dir / "inventory.md"
    md_lines = [
        "# App Discovery Inventory",
        "",
        f"- **Base URL:** {start_url}",
        f"- **Viewport:** {w}x{h}",
        f"- **Pages Discovered:** {len(pages_discovered)}",
        "",
        "## Pages Overview",
        "",
        "| # | Title | URL | Elements | Facts | Screenshot |",
        "|---|---|---|---|---|---|",
    ]
    for i, p in enumerate(pages_discovered):
        md_lines.append(f"| {i+1} | {p['title']} | `{p['url']}` | {len(p['elements'])} | {len(p['facts'])} | [{p['screenshot']}]({p['screenshot']}) |")

    md_lines.extend([
        "",
        "## Key Facts Sample",
        "",
        "| Fact Text | Context | Page URL | Target |",
        "|---|---|---|---|",
    ])
    sample_facts_seen = set()
    sample_count = 0
    for p in pages_discovered:
        for f in p["facts"]:
            if f["text"] not in sample_facts_seen and sample_count < 30:
                sample_facts_seen.add(f["text"])
                sample_count += 1
                target_str = json.dumps(f["target"], ensure_ascii=False)
                md_lines.append(f"| `{f['text']}` | {f['context']} | `{p['url']}` | `{target_str}` |")

    md_file.write_text("\n".join(md_lines), encoding="utf-8")
    print(f" Summary Markdown saved to: {md_file}")

    return inventory


def main():
    parser = argparse.ArgumentParser(description="App discovery for screendemo videos.")
    parser.add_argument("start_url", help="Start URL to crawl/discover")
    parser.add_argument("--out", required=True, help="Output JSON path (e.g. inventory.json)")
    parser.add_argument("--cdp", default="9350", help="CDP port or URL (default: 9350)")
    parser.add_argument("--max-pages", type=int, default=25, help="Maximum pages to discover (default: 25)")
    parser.add_argument("--viewport", default="1080x1350", help="Viewport size WxH (default: 1080x1350)")
    args = parser.parse_args()

    m = re.match(r"^(\d+)[xX](\d+)$", args.viewport.strip())
    if not m:
        raise ValueError(f"Invalid viewport format: {args.viewport}. Expected WxH like 1080x1350")
    vw, vh = int(m.group(1)), int(m.group(2))

    discover_site(
        start_url=args.start_url,
        out_json_path=args.out,
        cdp=args.cdp,
        max_pages=args.max_pages,
        viewport=(vw, vh),
    )


if __name__ == "__main__":
    main()
