#!/usr/bin/env python
"""领取入口。

    python main.py            # 领取所有进行中的活动
    python main.py --list     # 只列出活动，不领取
    python main.py --url URL  # 只处理指定活动（可多次）
    python main.py --limit 3  # 只处理前 3 个（调试）
"""
import argparse
import sys
from datetime import datetime

from playwright.sync_api import sync_playwright

from cfclaim import browser as browser_mod
from cfclaim import notify
from cfclaim.activities import Activity, fetch_activities
from cfclaim.claimer import claim_activity
from cfclaim.config import ROOT, load_adapters, load_config
from cfclaim.log import get_logger

log = get_logger()


def cmd_list(cfg):
    acts = fetch_activities(cfg)
    print(f"共 {len(acts)} 个进行中的活动：")
    for a in acts:
        rng = f"{a.start:%m-%d}~{a.end:%m-%d}" if a.start and a.end else "??"
        print(f"  [{rng}] {a.title}\n        {a.url}")


def cmd_claim(cfg, args):
    auth = ROOT / cfg["auth_file"]
    if not auth.exists():
        log.error(f"未找到登录态 {auth}，请先运行：python login.py")
        sys.exit(1)
    if args.headless:
        cfg["browser"]["headless"] = True
    adapters = load_adapters(cfg)

    if args.url:
        acts = [Activity("(命令行)", u) for u in args.url]
    else:
        acts = fetch_activities(cfg)
        log.info(f"找到 {len(acts)} 个进行中的活动")
    if args.limit:
        acts = acts[: args.limit]
    if not acts:
        log.info("没有需要处理的活动")
        return

    shot_dir = ROOT / cfg["output_dir"] / datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    with sync_playwright() as pw:
        browser, ctx = browser_mod.launch(pw, cfg, storage_state=auth)
        try:
            for i, a in enumerate(acts, 1):
                log.info(f"[{i}/{len(acts)}] {a.title}")
                try:
                    res = claim_activity(ctx, a, cfg, adapters, log, shot_dir)
                except Exception as e:
                    log.error(f"  异常：{e}")
                    res = []
                for r in res:
                    log.info(f"    {r.outcome:8s} {r.element}  {r.detail}")
                all_results += res
                if res and res[0].outcome == "需登录":
                    log.error("登录态已失效，请重新运行：python login.py")
                    break
        finally:
            try:
                browser_mod.save_state(ctx, auth)  # 刷新登录态
            except Exception:
                pass
            browser.close()

    ok = [r for r in all_results
          if r.outcome.startswith("成功") or r.outcome == "已领过"]
    summary = (f"活动 {len(acts)} 个，领取动作 {len(all_results)} 次，"
               f"成功/已领 {len(ok)}")
    log.info(summary)
    lines = [f"{r.activity}: {r.outcome}" for r in all_results[:30]]
    notify.send(cfg, "CF每日领取完成", summary + "\n" + "\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description="CF 活动自动领取")
    ap.add_argument("--config", default=None, help="配置文件路径")
    ap.add_argument("--headless", action="store_true", help="无头模式（不推荐，易被检测）")
    ap.add_argument("--list", action="store_true", help="只列出活动，不领取")
    ap.add_argument("--url", action="append", default=[], help="只处理指定活动URL（可多次）")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个活动（调试用）")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.list:
        cmd_list(cfg)
    else:
        cmd_claim(cfg, args)


if __name__ == "__main__":
    main()
