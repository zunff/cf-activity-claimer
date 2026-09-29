"""UI 与后台线程共享的状态，全部加锁访问。"""
import threading
import time
from collections import deque


class State:
    def __init__(self):
        self._lock = threading.Lock()
        self.status = "idle"       # idle | logging_in | claiming | done | error
        self.message = ""
        self.login_step = ""
        self.activities = []
        self.results = []
        self.logs = deque(maxlen=400)
        self._qr = None
        self.qr_seq = 0

    # ---- 写 ----
    def log(self, msg):
        with self._lock:
            self.logs.append(f"{time.strftime('%H:%M:%S')} {msg}")

    def set(self, **kw):
        with self._lock:
            for k, v in kw.items():
                setattr(self, k, v)

    def set_qr(self, png):
        with self._lock:
            if png and png != self._qr:
                self._qr = png
                self.qr_seq += 1

    def clear_qr(self):
        with self._lock:
            self._qr = None
            self.qr_seq += 1

    def reset_run(self):
        with self._lock:
            self.results = []

    # ---- 读 ----
    def get_qr(self):
        with self._lock:
            return self._qr

    def snapshot(self):
        with self._lock:
            return {
                "status": self.status,
                "message": self.message,
                "login_step": self.login_step,
                "has_qr": self._qr is not None,
                "qr_seq": self.qr_seq,
                "activities": list(self.activities),
                "results": list(self.results),
                "logs": list(self.logs),
            }
