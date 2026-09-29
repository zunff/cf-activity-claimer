"""后台线程：独占 Playwright，处理 UI 发来的命令（登录 / 领取 / 列活动）。"""
import queue
import random
import threading
import time
from dataclasses import asdict
from pathlib import Path

from playwright.sync_api import sync_playwright

from .. import browser as bmod
from ..activities import fetch_activities
from ..claimer import claim_activity
from ..config import ROOT, load_adapters
from . import qr


class _LogShim:
    """把 State.log 包成 claimer 需要的 logger 接口。"""
    def __init__(self, fn):
        self._fn = fn

    def info(self, m):
        self._fn(str(m))

    def warning(self, m):
        self._fn(str(m))

    def error(self, m):
        self._fn("错误：" + str(m))


def _act_dict(a):
    rng = f"{a.start:%m-%d}~{a.end:%m-%d}" if a.start and a.end else ""
    return {"title": a.title, "url": a.url, "range": rng}


class BrowserWorker(threading.Thread):
    def __init__(self, cfg, state):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.state = state
        self.q = queue.Queue()
        self.pw = None
        self.browser = None
        self.ctx = None

    def submit(self, cmd):
        self.q.put(cmd)

    # ---- 线程主循环 ----
    def run(self):
        while True:
            cmd = self.q.get()
            try:
                self._dispatch(cmd)
            except Exception as e:
                self.state.log(f"异常：{e}")
                self.state.set(status="error", message=str(e)[:140])

    def _dispatch(self, cmd):
        kind = cmd[0]
        if kind == "login":
            self._do_login()
        elif kind == "claim":
            self._do_claim()
        elif kind == "list":
            self._do_list()
        elif kind == "reset":
            self._close_ctx()
            self.state.set(status="idle", message="已重置")
        elif kind == "stop":
            self._shutdown()

    def _shutdown(self):
        self._close_ctx()
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.pw:
            try:
                self.pw.stop()
            except Exception:
                pass
            self.pw = None

    def _close_ctx(self):
        if self.ctx:
            try:
                self.ctx.close()
            except Exception:
                pass
            self.ctx = None

    def _new_context(self, use_auth=False):
        if self.pw is None:
            self.pw = sync_playwright().start()
        if self.browser is None:
            self.browser = bmod.launch_browser(self.pw, self.cfg)
        self._close_ctx()
        auth = (ROOT / self.cfg["auth_file"]) if use_auth else None
        self.ctx = bmod.new_context(self.browser, self.cfg, storage_state=auth)
        return self.ctx

    # ---- 命令实现 ----
    def _do_list(self):
        self.state.set(status="claiming", message="正在获取活动列表…")
        try:
            acts = fetch_activities(self.cfg)
        except Exception as e:
            self.state.set(status="error", message=f"获取活动失败：{e}")
            return
        self.state.set(activities=[_act_dict(a) for a in acts],
                       status="idle", message=f"共 {len(acts)} 个进行中的活动")
        self.state.log(f"获取到 {len(acts)} 个进行中的活动")

    def _do_login(self):
        self.state.set(status="logging_in", message="正在打开登录页…", login_step="")
        self.state.clear_qr()
        ctx = self._new_context()
        page = ctx.new_page()
        if not qr.open_login(page, self.state.log):
            self.state.set(status="error", message="没找到登录入口，请稍后重试")
            return
        self.state.log("请用手机 QQ 扫描页面上的二维码")

        deadline = time.time() + self.cfg.get("login_timeout_s", 600)
        last_step = None
        while time.time() < deadline:
            png = qr.capture_qr(page)
            if png:
                self.state.set_qr(png)
                self.state.set(message="请用手机 QQ 扫码登录")
            step = qr.login_step(page)
            if step and step != last_step:
                self.state.log(f"登录状态：{step}")
                last_step = step
            self.state.set(login_step=step)

            ok, names = qr.logged_in(ctx)
            if ok:
                self.state.log(f"检测到登录 Cookie：{sorted(names)}")
                page.wait_for_timeout(1500)
                bmod.save_state(ctx, ROOT / self.cfg["auth_file"])
                self.state.clear_qr()
                self.state.set(status="idle", login_step="",
                               message="登录成功，登录态已保存")
                self.state.log("登录态已保存到 auth.json")
                return
            qr.refresh_if_expired(page)
            time.sleep(1.5)

        self.state.clear_qr()
        self.state.set(status="error", message="登录超时")

    def _do_claim(self):
        auth = ROOT / self.cfg["auth_file"]
        if not auth.exists():
            self.state.set(status="error", message="还没有登录态，请先点「开始登录」")
            return
        self.state.reset_run()
        self.state.set(status="claiming", message="正在获取活动列表…")
        try:
            acts = fetch_activities(self.cfg)
        except Exception as e:
            self.state.set(status="error", message=f"获取活动失败：{e}")
            return
        self.state.set(activities=[_act_dict(a) for a in acts])
        if not acts:
            self.state.set(status="done", message="没有进行中的活动")
            return

        ctx = self._new_context(use_auth=True)
        adapters = load_adapters(self.cfg)
        shot_dir = ROOT / self.cfg["output_dir"] / time.strftime("%Y%m%d_%H%M%S")
        shot_dir.mkdir(parents=True, exist_ok=True)
        log = _LogShim(self.state.log)

        results = []
        logged_out = False
        for i, a in enumerate(acts, 1):
            self.state.set(message=f"[{i}/{len(acts)}] {a.title}")
            self.state.log(f"[{i}/{len(acts)}] {a.title}")
            try:
                res = claim_activity(ctx, a, self.cfg, adapters, log, shot_dir)
            except Exception as e:
                self.state.log(f"异常：{e}")
                res = []
            for r in res:
                self.state.log(f"  {r.outcome}　{r.element}　{r.detail}")
                results.append(asdict(r))
            self.state.set(results=list(results))
            if res and res[0].outcome == "需登录":
                logged_out = True
                break
            time.sleep(random.uniform(0.5, 1.2))

        try:
            bmod.save_state(ctx, auth)
        except Exception:
            pass

        if logged_out:
            self.state.set(status="error", message="登录态已失效，请重新登录")
        else:
            ok = sum(1 for r in results if r["outcome"].startswith("成功") or r["outcome"] == "已领过")
            self.state.set(status="done",
                           message=f"完成：{len(results)} 次领取动作，成功/已领 {ok}")
