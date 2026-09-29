"""从 WMP 接口枚举 CF 活动，并按时间判断是否进行中。无需登录。"""
from dataclasses import dataclass
from datetime import datetime

import requests

API = "https://apps.game.qq.com/wmp/v3.1/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class Activity:
    title: str
    url: str
    start: datetime | None = None
    end: datetime | None = None
    note: str = ""
    in_progress: bool = True


def _parse_time(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


def _parse_item(it):
    desc = (it.get("sDesc") or "").split("|")
    start = _parse_time(desc[0]) if len(desc) > 0 else None
    end = _parse_time(desc[1]) if len(desc) > 1 else None
    note = desc[2] if len(desc) > 2 else ""
    now = datetime.now()
    in_progress = bool(start and end and start <= now <= end)
    return Activity(it.get("sTitle", "").strip(), it.get("sRedirectURL", "").strip(),
                    start, end, note, in_progress)


def fetch_activities(cfg, session=None):
    acfg = cfg["activities"]
    session = session or requests.Session()
    session.headers.update({"User-Agent": UA, "Referer": "https://cf.qq.com/"})

    items, page, total = [], 1, 1
    while page <= total and page <= acfg.get("max_pages", 10):
        params = {
            "p0": 1, "p1": "searchNewsKeywordsList", "page": page,
            "pagesize": acfg.get("pagesize", 50), "order": "sIdxTime", "r0": "json",
            "type": "iTag", "id": acfg.get("tag_id", "1487"), "source": "web_pc",
        }
        r = session.get(API, params=params, timeout=20)
        msg = r.json().get("msg", {})
        total = int(msg.get("totalpage", 1) or 1)
        items += msg.get("result", []) or []
        page += 1

    seen, result = set(), []
    for it in items:
        a = _parse_item(it)
        if not a.url or a.url in seen:
            continue
        seen.add(a.url)
        result.append(a)

    if cfg["claim"].get("only_in_progress", True):
        result = [a for a in result if a.in_progress]

    for u in acfg.get("extra_urls", []) or []:
        if u not in seen:
            seen.add(u)
            result.append(Activity("(手动添加)", u, None, None, "", True))

    return result
