"""半自动登录：打开 CF 页面，用户自己完成登录，程序检测成功后由调用方保存登录态。"""
import time

LOGIN_URL = "https://cf.qq.com/web202410/actions.html"

# QQ 登录成功后会在 .qq.com 域写入这些 cookie
AUTH_COOKIE_NAMES = {"skey", "p_skey", "p_uin", "uin", "luin", "ptui_loginuin"}


def _auth_cookies(ctx):
    found = set()
    for c in ctx.cookies():
        if not c.get("value"):
            continue
        if "qq.com" in (c.get("domain") or "") and c["name"] in AUTH_COOKIE_NAMES:
            found.add(c["name"])
    return found


def run_login(ctx, cfg, log, timeout_s=None):
    timeout_s = timeout_s or cfg.get("login_timeout_s", 600)
    page = ctx.new_page()
    log.info("打开 CF 活动页，请在弹出的真实 Chrome 里完成登录")
    log.info("扫码 / 账号密码 / 短信验证都手动完成即可，程序会自动检测登录成功")
    log.info("如果没有自动识别到，登录完直接按 Ctrl+C 也会保存当前登录态")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    deadline = time.time() + timeout_s
    last = 0.0
    while time.time() < deadline:
        names = _auth_cookies(ctx)
        if names & {"uin", "p_uin", "skey", "p_skey"}:
            log.info(f"检测到登录 Cookie: {sorted(names)}")
            page.wait_for_timeout(1500)
            return True
        if time.time() - last > 15:
            log.info("仍在等待登录...")
            last = time.time()
        time.sleep(2)
    log.warning("等待登录超时")
    return False
