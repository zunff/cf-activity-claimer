"""领取引擎：遍历活动页所有 frame，找领取按钮 -> 点击 -> 判断结果。"""
import random
import time
from dataclasses import dataclass
from pathlib import Path

# 在单个 frame 内扫描候选按钮。存句柄到 window.__cfc，避免重渲染后选择器失效。
SCAN_JS = r"""
() => {
  const KW = /领取/;
  window.__cfc = [];
  const cands = [];
  for (const el of document.querySelectorAll('a,button,div,span,li,img,input')) {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (!(r.width > 2 && r.height > 2)) continue;
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    if (parseFloat(s.opacity || '1') < 0.1) continue;
    const text = (el.innerText || el.getAttribute('alt') || el.getAttribute('title') || el.value || '').trim();
    const href = el.getAttribute('href') || '';
    const cls = (el.className || '').toString();
    const flat = text.replace(/\s/g, '');
    const textHit = KW.test(flat) && flat.length <= 14;
    const hrefHit = href.indexOf('javascript:') === 0 && KW.test(flat);
    const clsHit = /(btn[-_]?lq|lq[-_]?btn|lingqu|btn[-_]?claim|claim[-_]?btn|receive)/i.test(cls);
    if (textHit || hrefHit || clsHit) cands.push(el);
  }
  const inner = cands.filter(el => !cands.some(o => o !== el && el.contains(o)));
  window.__cfc = inner;
  inner.forEach((el, i) => el.setAttribute('data-cf-claim', String(i)));
  return inner.map((el, i) => ({
    idx: i,
    tag: el.tagName,
    cls: (el.className || '').toString().slice(0, 60),
    text: (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 24),
    href: (el.getAttribute('href') || '').slice(0, 50),
  }));
}
"""

# 用 JS 直接点击（对 javascript: 链接最稳，兜底用）
CLICK_JS = r"""
(i) => {
  const el = (window.__cfc || [])[i];
  if (!el) return 'gone';
  try { el.scrollIntoView({block: 'center'}); } catch (e) {}
  el.click();
  return 'ok';
}
"""

# 读取真正的弹窗文字：只取定位过 / 有 z-index 的元素，按 z-index 从高到低
RESULT_JS = r"""
() => {
  const vw = innerWidth, vh = innerHeight, seen = new Set(), items = [];
  for (const el of document.querySelectorAll('div,section,p,span,a')) {
    const cls = (el.className || '').toString();
    if (!/pop|modal|dialog|tips|toast|alert|msg|result|tip/i.test(cls)) continue;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (r.width < 40 || r.height < 16) continue;
    if (s.display === 'none' || s.visibility === 'hidden') continue;
    if (parseFloat(s.opacity || '1') < 0.1) continue;
    const zi = parseInt(s.zIndex, 10);
    const z = isNaN(zi) ? 0 : zi;
    if (s.position === 'static' && z <= 0) continue;
    if (r.width > vw * 0.92 && r.height > vh * 0.6) continue;
    const t = (el.innerText || '').trim().replace(/\s+/g, ' ');
    if (!t || t.length > 60 || seen.has(t)) continue;
    seen.add(t);
    items.push({t, z});
  }
  items.sort((a, b) => b.z - a.z);
  return items.slice(0, 10).map(x => x.t);
}
"""

LOGIN_SELECTORS = [
    ".qcwx-login-cover", "#qcwx-login", ".milo-qcwx-login",
    "iframe#milo-qcwx-frame-qc",
    "iframe[src*='ptlogin2']",
    "iframe[src*='graph.qq.com/oauth2']",
]


@dataclass
class ClaimResult:
    activity: str
    url: str
    element: str
    outcome: str
    detail: str = ""


def _is_claim_request(req):
    u = req.url
    if "ams.game.qq.com" not in u:
        return False
    if "/log" in u or "sCloudApiName=atm" in u:
        return False
    return True


def _login_overlay(page):
    for sel in LOGIN_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return True
        except Exception:
            pass
    return False


def classify(texts):
    joined = " ".join(texts)
    if not joined:
        return "无反馈"
    if any(k in joined for k in ["已领取", "已领过", "重复领取", "已经领取"]):
        return "已领过"
    if any(k in joined for k in ["成功", "恭喜", "领取成功"]):
        return "成功"
    if any(k in joined for k in ["登录", "登陆"]):
        return "需登录"
    if any(k in joined for k in ["未开始", "未达成", "不满足", "不符合", "尚未",
                                 "无法", "未完成", "条件", "暂未"]):
        return "未达标"
    return "未知"


def _read_texts(page, frame):
    texts = []
    for target in (frame, page.main_frame):
        try:
            texts += target.evaluate(RESULT_JS)
        except Exception:
            pass
    return list(dict.fromkeys(texts))


def _match_adapter(adapters, url):
    for pattern, ad in adapters.items():
        if pattern in url:
            return ad
    return None


def _dismiss(page, adapter):
    for sel in (adapter or {}).get("pre_dismiss", []):
        for fr in page.frames:
            try:
                loc = fr.locator(sel)
                if loc.count() and loc.first.is_visible():
                    loc.first.click(timeout=2000)
                    page.wait_for_timeout(300)
            except Exception:
                pass
    for kw in ("我知道了", "知道了"):
        for fr in page.frames:
            try:
                loc = fr.get_by_text(kw, exact=True)
                if loc.count() and loc.first.is_visible():
                    loc.first.click(timeout=1500)
                    page.wait_for_timeout(200)
            except Exception:
                pass


def _slug(s):
    out = "".join(ch for ch in s if ch.isalnum() or ch in "_-")
    return out[:20] or "activity"


def claim_activity(ctx, activity, cfg, adapters, log, shot_dir):
    page = ctx.new_page()
    page.set_default_timeout(cfg["browser"]["nav_timeout_ms"])
    results = []
    claim_log = []
    page.on("request", lambda r: claim_log.append(r.url) if _is_claim_request(r) else None)
    try:
        log.info(f"  打开 {activity.url}")
        page.goto(activity.url, wait_until="domcontentloaded",
                  timeout=cfg["browser"]["nav_timeout_ms"])
        page.wait_for_timeout(cfg["browser"]["page_wait_ms"])

        adapter = _match_adapter(adapters, activity.url)
        _dismiss(page, adapter)

        cands = []          # (frame, idx|None, css_selector|None, label)
        seen_labels = set()
        for fr in page.frames:
            if adapter and adapter.get("buttons"):
                for sel in adapter["buttons"]:
                    try:
                        cnt = fr.locator(sel).count()
                    except Exception:
                        cnt = 0
                    for i in range(cnt):
                        cands.append((fr, None, f"{sel} >> nth={i}", sel))
            else:
                try:
                    found = fr.evaluate(SCAN_JS)
                except Exception:
                    continue
                for c in found:
                    label = f'{c["tag"]}.{c["cls"]} "{c["text"]}"'.strip()
                    if label in seen_labels:
                        continue
                    seen_labels.add(label)
                    cands.append((fr, c["idx"], None, label))

        if not cands:
            overlay = "需登录" if _login_overlay(page) else "无可领取"
            detail = "出现登录框，请先 python login.py" if overlay == "需登录" else "未找到领取按钮"
            return [ClaimResult(activity.title, activity.url, "-", overlay, detail)]

        if _login_overlay(page):
            return [ClaimResult(activity.title, activity.url, "-", "需登录",
                                "出现登录框，请先 python login.py")]

        for fr, idx, sel, label in cands:
            before = len(claim_log)
            clicked = False
            if sel:                                     # 适配器选择器：原生点击
                try:
                    fr.click(sel, timeout=4000)
                    clicked = True
                except Exception:
                    pass
            else:                                       # 通用候选：原生点击优先，JS 兜底
                try:
                    fr.click(f'[data-cf-claim="{idx}"]', timeout=4000)
                    clicked = True
                except Exception:
                    try:
                        clicked = fr.evaluate(CLICK_JS, idx) == "ok"
                    except Exception:
                        clicked = False
            if not clicked:
                results.append(ClaimResult(activity.title, activity.url, label,
                                           "点击失败", "元素已失效或被遮挡"))
                continue

            page.wait_for_timeout(cfg["claim"]["result_wait_ms"])
            texts = _read_texts(page, fr)
            outcome = classify(texts)
            if outcome in ("无反馈", "未知") and _login_overlay(page):
                outcome, texts = "需登录", ["点击后弹出登录框"]
            if outcome == "无反馈" and len(claim_log) > before:
                outcome = "成功(接口)"
            results.append(ClaimResult(activity.title, activity.url, label,
                                       outcome, " | ".join(texts)[:90]))
            if outcome == "需登录":
                break  # 未登录，其余按钮也只会弹登录框
            if outcome == "未知" and cfg["claim"].get("screenshot"):
                try:
                    page.screenshot(
                        path=str(Path(shot_dir) / f"{_slug(activity.title)}_{label[:8]}.png"))
                except Exception:
                    pass
            time.sleep(random.uniform(*cfg["claim"]["click_delay"]))
    finally:
        page.close()
    return results
