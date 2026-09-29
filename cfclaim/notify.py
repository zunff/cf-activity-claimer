"""结果通知：默认打印，可配置企业微信/钉钉等 webhook。"""
import json
import urllib.request


def send(cfg, title, text):
    webhook = (cfg.get("notify") or {}).get("webhook") or ""
    if not webhook:
        return
    # 企业微信机器人 text 格式；钉钉改成 {"msgtype":"text","text":{"content":...}} 亦可
    payload = json.dumps(
        {"msgtype": "text", "text": {"content": f"{title}\n{text}"}}
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:  # 通知失败不影响主流程
        print("通知发送失败:", e)
