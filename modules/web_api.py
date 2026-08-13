"""
web_api.py — Flask endpoints that run on Render (orchestrator side).
The PC producer POSTs staged content here; the health check keeps Render awake.
Auth: shared secret header (STAGE_TOKEN) so only your PC can push.
"""
import os, sys, json, io, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "modules"))
from flask import Flask, request, jsonify
import state_db

app = Flask(__name__)


def _auth():
    tok = request.headers.get("X-Stage-Token", "")
    expected = os.environ.get("STAGE_TOKEN", "")
    return bool(expected) and hashlib.sha256(tok.encode()).hexdigest() == \
        hashlib.sha256(expected.encode()).hexdigest()


@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "social-agent-render", "stats": state_db.stats()})


@app.route("/api/stage", methods=["POST"])
def stage():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True, silent=True) or {}
    # data: {id, pillar, slot, topic, reel_url, info_url, caption, hook, platforms}
    if not data.get("id"):
        return jsonify({"error": "missing id"}), 400
    data["status"] = "staged"
    state_db.add_item(data)
    state_db.log("INFO", f"staged {data.get('pillar')}/{data.get('slot')} topic={data.get('topic')}")
    return jsonify({"ok": True, "id": data["id"]})


@app.route("/api/pending", methods=["GET"])
def pending():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"items": state_db.pending()})


@app.route("/api/set_published", methods=["POST"])
def set_published():
    if not _auth():
        return jsonify({"error": "unauthorized"}), 401
    d = request.get_json(force=True, silent=True) or {}
    state_db.set_published(d.get("id"), d.get("platforms", []))
    return jsonify({"ok": True})


@app.route("/api/bot_status")
def bot_status():
    import state_db as _db
    return jsonify({
        "telegram_alive": _db.get_flag("bot_Telegram_alive") == "1",
        "bale_alive": _db.get_flag("bot_Bale_alive") == "1",
    })


if __name__ == "__main__":
    state_db.init()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
