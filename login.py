#!/usr/bin/env python
"""登录入口：python login.py  —— 手动登录一次，保存登录态到 auth.json。"""
import sys

from playwright.sync_api import sync_playwright

from cfclaim import browser as browser_mod
from cfclaim.config import ROOT, load_config
from cfclaim.log import get_logger
from cfclaim.login import run_login


def main():
    log = get_logger()
    cfg = load_config()
    cfg["browser"]["headless"] = False  # 登录必须有界面

    auth = ROOT / cfg["auth_file"]
    with sync_playwright() as pw:
        browser, ctx = browser_mod.launch(pw, cfg)
        try:
            ok = run_login(ctx, cfg, log)
        except KeyboardInterrupt:
            log.info("收到中断，保存当前登录态...")
            ok = True
        finally:
            browser_mod.save_state(ctx, auth)
            browser.close()

    if ok:
        log.info(f"登录态已保存：{auth}")
    else:
        log.error("登录未完成，请重试")
        sys.exit(1)


if __name__ == "__main__":
    main()
