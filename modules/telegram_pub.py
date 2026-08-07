"""
telegram_pub.py — publishes to a PRIVATE channel first (approval_required).
Owner reviews; sends /publish <id> to approve -> moves to PUBLIC channel.
Uses python-telegram-bot + urllib (no extra deps if token present).
"""
import os, json, sys, urllib.request, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))


def _tok():
    return os.environ.get(CFG["telegram"]["bot_token_env"], "")


def _api(method, payload):
    tok = _tok()
    url = f"https://api.telegram.org/bot{tok}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stage_private(chat_id, media_path, caption, kind="photo"):
    """Send to private approval channel. kind: photo | video | document."""
    cap = (caption or "")[:1024]
    if kind == "video":
        return _api("sendVideo", {"chat_id": chat_id, "video": media_path, "caption": cap})
    if kind == "document":
        return _api("sendDocument", {"chat_id": chat_id, "document": media_path, "caption": cap})
    return _api("sendPhoto", {"chat_id": chat_id, "photo": media_path, "caption": cap})


def publish_public(channel, media_path, caption, kind="photo"):
    return stage_private(channel, media_path, caption, kind)


def poll_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset: params["offset"] = offset
    return _api("getUpdates", params)


if __name__ == "__main__":
    print("telegram_pub loaded. Set TELEGRAM_BOT_TOKEN to use.")
