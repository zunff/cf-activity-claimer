"""浏览器启动封装：真 Chrome + 基础反自动化检测。"""
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
"""

ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-infobars",
]


def launch_browser(pw, cfg):
    b = cfg["browser"]
    return pw.chromium.launch(
        channel=b.get("channel") or None,
        headless=bool(b.get("headless")),
        args=ARGS,
        ignore_default_args=["--enable-automation"],
    )


def new_context(browser, cfg, storage_state=None):
    b = cfg["browser"]
    kwargs = dict(
        locale=b.get("locale", "zh-CN"),
        user_agent=UA,
        viewport={"width": 1440, "height": 900},
        timezone_id="Asia/Shanghai",
        device_scale_factor=b.get("device_scale_factor", 2),
    )
    if storage_state and Path(storage_state).exists():
        kwargs["storage_state"] = str(storage_state)
    ctx = browser.new_context(**kwargs)
    ctx.add_init_script(STEALTH_JS)
    ctx.set_default_timeout(b.get("nav_timeout_ms", 60000))
    return ctx


def launch(pw, cfg, storage_state=None):
    browser = launch_browser(pw, cfg)
    return browser, new_context(browser, cfg, storage_state)


def save_state(ctx, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ctx.storage_state(path=str(p))
