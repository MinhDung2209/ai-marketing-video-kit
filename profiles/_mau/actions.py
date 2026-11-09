"""Thao tác riêng của web doanh nghiệp (khi các bước chung của shoot.py không đủ). Dùng trong shots.json: {"do": "ten_ham", ...}.
Mỗi hàm nhận r = shoot.Runner: r.s = rec.Session (click/type/focus/mark_text/…), r.loc(target), r.check_click(locator), r.V (biến).
Ví dụ thật: KIT/profiles/stradevn/actions.py (bấm tab, chép báo cáo trong iframe, tạo chiến dịch có chặn an toàn)."""


def open_menu(r, name, wait=1.0):
    """Ví dụ: bấm mục menu bên trái theo tên."""
    l = r.s.page.locator("nav a, nav button").filter(has_text=name).first
    r.check_click(l); r.s.click(l); r.s.wait(wait)
