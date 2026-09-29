#!/usr/bin/env python
"""本地 Web UI 入口：python ui.py  —— 浏览器里扫码登录 + 一键领取。"""
import argparse
import threading
import webbrowser

from cfclaim.config import load_config
from cfclaim.ui.server import create_app
from cfclaim.ui.state import State
from cfclaim.ui.worker import BrowserWorker


def main():
    ap = argparse.ArgumentParser(description="CF 活动自动领取 · 本地 UI")
    ap.add_argument("--host", default=None, help="监听地址（默认取配置）")
    ap.add_argument("--port", type=int, default=None, help="端口（默认取配置）")
    ap.add_argument("--show-browser", action="store_true",
                    help="显示真实浏览器窗口（默认无头，二维码只显示在页面里）")
    ap.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = ap.parse_args()

    cfg = load_config()
    ui = cfg["ui"]
    host = args.host or ui.get("host", "127.0.0.1")
    port = args.port or ui.get("port", 8765)

    cfg["browser"]["headless"] = not args.show_browser and bool(ui.get("headless", True))

    state = State()
    worker = BrowserWorker(cfg, state)
    worker.start()

    app = create_app(cfg, state, worker)
    url = f"http://{host}:{port}/"
    if not args.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"UI 已启动：{url}    （Ctrl+C 退出）")
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
