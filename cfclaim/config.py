"""配置加载：默认值 + config.json 覆盖 + adapters.json。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT = {
    "auth_file": "auth.json",
    "output_dir": "output",
    "adapters_file": "adapters.json",
    "login_timeout_s": 600,
    "browser": {
        "headless": False,
        "channel": "chrome",
        "locale": "zh-CN",
        "nav_timeout_ms": 60000,
        "page_wait_ms": 6000,
    },
    "claim": {
        "only_in_progress": True,
        "click_delay": [0.8, 2.0],
        "result_wait_ms": 2500,
        "screenshot": True,
    },
    "activities": {
        "tag_id": "1487",
        "pagesize": 50,
        "max_pages": 10,
        "extra_urls": [],
    },
    "notify": {"webhook": ""},
    "ui": {
        "host": "127.0.0.1",
        "port": 8765,
        "headless": True,
    },
}


def _merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path=None):
    p = Path(path) if path else ROOT / "config.json"
    user = {}
    if p.exists():
        user = json.loads(p.read_text(encoding="utf-8"))
    return _merge(DEFAULT, user)


def load_adapters(cfg):
    p = ROOT / cfg["adapters_file"]
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}
