"""Trình dựng đồ hoạ chèn (motion inserts) cho video demo sản phẩm (screendemo).
Hỗ trợ 4 loại: counter, card_stack, route, compare.
HTML + CSS + GSAP, hiển thị 1080x1920 tràn viền bên trong vùng an toàn (safe areas).
"""
import html, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
INSERTS_DIR = HERE / "templates" / "inserts"


def fmt_vi_number(val, decimals=None):
    """Định dạng số theo chuẩn tiếng Việt: chấm (.) phân tách nghìn, phẩy (,) phân tách thập phân."""
    try:
        f = float(val)
    except (ValueError, TypeError):
        return str(val)

    if decimals is None:
        decimals = 2 if not f.is_integer() and round(f, 2) != round(f, 0) else 0

    if decimals == 0:
        return f"{int(round(f)):,}".replace(",", ".")
    else:
        formatted = f"{f:.{decimals}f}"
        int_part, dec_part = formatted.split(".")
        int_part = f"{int(int_part):,}".replace(",", ".")
        return f"{int_part},{dec_part}"


def get_inserts_css():
    """Đọc toàn bộ CSS của inserts để gắn vào index.html."""
    css_file = INSERTS_DIR / "inserts.css"
    if css_file.exists():
        return css_file.read_text(encoding="utf-8")
    return ""


def render_insert(kind, iid, t, dur=1.6, mode="overlay", **data):
    """Render 1 insert thành (html_snippet, js_snippet, reveal_time).
    kind: 'counter', 'card_stack', 'route', 'compare'.
    """
    tpl_file = INSERTS_DIR / f"{kind}.html"
    if not tpl_file.exists():
        raise ValueError(f"Không tìm thấy template insert '{kind}' tại {tpl_file}")

    content = tpl_file.read_text(encoding="utf-8")
    parts = re.split(r"<script>", content, maxsplit=1)
    html_tpl = parts[0].strip()
    js_tpl = parts[1].replace("</script>", "").strip() if len(parts) > 1 else ""

    panel_class = "insert-cut" if mode == "cut" else "insert-overlay"
    kicker = data.get("kicker")
    kicker_html = f'<div class="ins-kicker"><span class="dot"></span><span>{html.escape(str(kicker))}</span></div>' if kicker else ""

    sub = data.get("sub") or data.get("subtitle")
    sub_html = f'<div class="ins-sub">{html.escape(str(sub))}</div>' if sub else ""

    subs = {
        "id": iid,
        "t": f"{t:.3f}",
        "dur": f"{dur:.3f}",
        "panel_class": panel_class,
        "kicker_html": kicker_html,
        "sub_html": sub_html,
    }

    if kind == "counter":
        val = data.get("value", 0)
        from_val = data.get("from_val", 0)
        unit = data.get("unit", "")
        label = data.get("label", "")
        decimals = data.get("decimals")
        if decimals is None:
            decimals = 2 if isinstance(val, float) and not val.is_integer() else 0

        count_dur = min(1.0, dur * 0.65)
        subs.update({
            "from_val": str(from_val),
            "from_val_fmt": fmt_vi_number(from_val, decimals),
            "to_val": str(val),
            "unit": html.escape(str(unit)),
            "label": html.escape(str(label)),
            "decimals": str(decimals),
            "count_dur": f"{count_dur:.3f}",
            "sub_anim": f"tl.fromTo('#{iid} .ins-sub', {{ opacity: 0 }}, {{ opacity: 1, duration: 0.35 }}, {t:.3f} + 0.45);" if sub else "",
        })
        reveal_time = round(t + 0.35, 3)

    elif kind == "card_stack":
        cards = data.get("cards", [])
        if not cards:
            raise ValueError("card_stack cần danh sách 'cards' (2-4 thẻ)")
        if len(cards) < 2:
            raise ValueError("card_stack cần ít nhất 2 thẻ")
        cards = cards[:4]

        title = data.get("title", "Top đối tác tiềm năng")
        subs["title"] = html.escape(str(title))

        cards_html_list = []
        cards_anim_list = []
        for i, c in enumerate(cards):
            rank = c.get("rank", i + 1)
            ctitle = html.escape(str(c.get("title", c.get("name", ""))))
            creason = html.escape(str(c.get("reason", c.get("desc", ""))))
            ctag = c.get("tag")
            tag_html = f'<div class="ins-card-tag">{html.escape(str(ctag))}</div>' if ctag else ""

            cid = f"{iid}_card_{i}"
            rank_cls = "rank-1" if rank == 1 else f"rank-{rank}"
            cards_html_list.append(
                f'<div class="ins-card {rank_cls}" id="{cid}">'
                f'<div class="ins-card-rank">{rank}</div>'
                f'<div class="ins-card-body">'
                f'<div class="ins-card-title">{ctitle}</div>'
                f'<div class="ins-card-reason">{creason}</div>'
                f'</div>{tag_html}</div>'
            )
            card_t = t + 0.15 + i * 0.12
            cards_anim_list.append(
                f"tl.fromTo('#{cid}', {{ x: 60, opacity: 0, scale: 0.94 }}, "
                f"{{ x: 0, opacity: 1, scale: 1, duration: 0.42, ease: 'back.out(1.4)', immediateRender: false }}, {card_t:.3f});"
            )
        subs["cards_html"] = "\n".join(cards_html_list)
        subs["cards_anim"] = "\n".join(cards_anim_list)
        reveal_time = round(t + 0.35, 3)

    elif kind == "route":
        from_city = data.get("from_city") or data.get("origin") or "Vũng Tàu"
        to_city = data.get("to_city") or data.get("dest") or "Chicago"
        weight = data.get("weight") or data.get("value") or ""
        stat = data.get("stat") or data.get("desc") or data.get("badge") or ""
        title = data.get("title", "HÀNH TRÌNH LÔ HÀNG")
        subtitle = data.get("subtitle", "Vận tải đường biển quốc tế")

        subs.update({
            "title": html.escape(str(title)),
            "subtitle": html.escape(str(subtitle)),
            "from_label": html.escape(str(from_city)),
            "to_label": html.escape(str(to_city)),
            "weight": html.escape(str(weight)),
            "stat": html.escape(str(stat)),
        })
        reveal_time = round(t + 0.82, 3)

    elif kind == "compare":
        title = data.get("title", "Soi đối thủ · Đơn giá theo nước")
        subtitle = data.get("subtitle", "Đơn giá trung vị xuất sang Mỹ (USD/kg)")

        item_a = data.get("before") or data.get("item_a") or {}
        item_b = data.get("after") or data.get("item_b") or {}

        val_a = float(item_a.get("value", 0))
        val_b = float(item_b.get("value", 0))
        dec_a = 2 if not val_a.is_integer() else 0
        dec_b = 2 if not val_b.is_integer() else 0

        max_v = max(val_a, val_b, 1.0) * 1.15
        h_a = max(30, round(val_a / max_v * 280, 1))
        h_b = max(30, round(val_b / max_v * 280, 1))

        delta_text = data.get("delta")
        direction = data.get("direction")
        if direction is None:
            if val_a < val_b:
                direction = "down"
            else:
                direction = "up"

        if not delta_text:
            diff = abs(val_b - val_a)
            delta_text = f"Chênh lệch: ${diff:.2f}/kg"

        arrow_svg = (
            '<path d="M12 4v13m0 0l-5-5m5 5l5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            if direction == "down"
            else '<path d="M12 20V7m0 0l-5 5m5-5l5 5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        )

        subs.update({
            "title": html.escape(str(title)),
            "subtitle": html.escape(str(subtitle)),
            "label_a": html.escape(str(item_a.get("label", "Việt Nam"))),
            "label_b": html.escape(str(item_b.get("label", "Mexico"))),
            "val_a_raw": str(val_a),
            "val_b_raw": str(val_b),
            "val_a_fmt": fmt_vi_number(val_a, dec_a),
            "val_b_fmt": fmt_vi_number(val_b, dec_b),
            "unit_a": html.escape(str(item_a.get("unit", "$/kg"))),
            "unit_b": html.escape(str(item_b.get("unit", "$/kg"))),
            "sub_a": html.escape(str(item_a.get("sub", ""))),
            "sub_b": html.escape(str(item_b.get("sub", ""))),
            "decimals_a": str(dec_a),
            "decimals_b": str(dec_b),
            "height_a": str(h_a),
            "height_b": str(h_b),
            "delta_dir": direction,
            "delta_text": html.escape(str(delta_text)),
            "arrow_svg": arrow_svg,
        })
        reveal_time = round(t + 0.85, 3)
    else:
        raise ValueError(f"Loại insert không hỗ trợ: {kind}")

    # Thay thế các biến trong template {{var}}
    def repl(m):
        k = m.group(1).strip()
        return str(subs.get(k, ""))

    rendered_html = re.sub(r"\{\{([^}]+)\}\}", repl, html_tpl)
    rendered_js = re.sub(r"\{\{([^}]+)\}\}", repl, js_tpl)

    custom_reveal = data.get("reveal_time")
    if custom_reveal is not None:
        reveal_time = float(custom_reveal)

    return rendered_html, rendered_js, reveal_time
