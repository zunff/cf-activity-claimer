"""Flask 应用：本地 UI 的 HTTP 接口。"""
from pathlib import Path

from flask import Flask, Response, jsonify

INDEX_HTML = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


def create_app(cfg, state, worker):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return Response(INDEX_HTML, mimetype="text/html")

    @app.get("/api/state")
    def api_state():
        return jsonify(state.snapshot())

    @app.get("/api/qr")
    def api_qr():
        png = state.get_qr()
        if not png:
            return Response("", status=404)
        return Response(png, mimetype="image/png",
                        headers={"Cache-Control": "no-store, max-age=0"})

    @app.post("/api/login")
    def api_login():
        state.reset_run()
        worker.submit(("login",))
        return jsonify(ok=True)

    @app.post("/api/claim")
    def api_claim():
        worker.submit(("claim",))
        return jsonify(ok=True)

    @app.post("/api/list")
    def api_list():
        worker.submit(("list",))
        return jsonify(ok=True)

    @app.post("/api/reset")
    def api_reset():
        worker.submit(("reset",))
        return jsonify(ok=True)

    return app
