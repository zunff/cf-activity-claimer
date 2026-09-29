"""登录触发 + 二维码抓取 + 扫码进度读取。"""
CF_HOME = "https://cf.qq.com/"
LOGIN_BUTTONS = ["a#dologin", "#dologin", ".unlogin-btn"]
QR_FRAME_HINT = ("ptlogin2.qq.com", "xlogin")
QR_SELECTORS = ["#qrlogin_img", "#qr_area", "#qlogin_show"]

AUTH_COOKIE_NAMES = {"skey", "p_skey", "p_uin", "uin", "luin", "ptui_loginuin"}


def open_login(page, log):
    """打开官网并触发登录弹窗。"""
    page.goto(CF_HOME, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    for sel in LOGIN_BUTTONS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click(timeout=5000)
                log("已点击官网登录按钮，等待二维码…")
                return True
        except Exception:
            pass
    for sel in (".qcwx-login-cover", "#qcwx-login"):   # 兜底：页面自带登录遮罩
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                log("页面已自带登录框")
                return True
        except Exception:
            pass
    return False


def _qr_frame(page):
    for fr in page.frames:
        u = fr.url or ""
        if QR_FRAME_HINT[0] in u and QR_FRAME_HINT[1] in u:
            return fr
    return None


def capture_qr(page):
    fr = _qr_frame(page)
    if not fr:
        return None
    for sel in QR_SELECTORS:
        try:
            el = fr.query_selector(sel)
            if not el:
                continue
            box = el.bounding_box()
            if box and box["width"] >= 50 and box["height"] >= 50:
                return el.screenshot()
        except Exception:
            pass
    return None


def login_step(page):
    fr = _qr_frame(page)
    if not fr:
        return ""
    for sel, label in (("#qrlogin_step3", "验证成功，正在登录中…"),
                       ("#qrlogin_step2", "已扫码，请在手机上确认"),
                       ("#qr_invalid", "二维码已过期，正在刷新…")):
        try:
            el = fr.query_selector(sel)
            if el and el.is_visible():
                return label
        except Exception:
            pass
    return "等待扫码"


def refresh_if_expired(page):
    fr = _qr_frame(page)
    if not fr:
        return
    try:
        el = fr.query_selector("#qr_invalid")
        if el and el.is_visible():
            el.click(timeout=2000)
    except Exception:
        pass


def logged_in(ctx):
    names = set()
    for c in ctx.cookies():
        if c.get("value") and "qq.com" in (c.get("domain") or "") and c["name"] in AUTH_COOKIE_NAMES:
            names.add(c["name"])
    return bool(names & {"skey", "p_skey", "uin", "p_uin"}), names
