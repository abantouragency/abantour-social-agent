"""
instagram_pub.py — official Instagram Graph API publishing (reels/photos).
Requires a Business/Creator IG account linked to a Facebook Page, plus a
long-lived access token (IG_ACCESS_TOKEN) and IG_USER_ID.
Stages first; a /publish approval moves it live.
"""
import os, json, sys, urllib.request, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))


def _get(k):
    return os.environ.get(CFG["instagram"][k], "")


def _post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def create_container(media_path_or_url, caption, is_reel=False):
    """Create a media container. For local files you must host them or use a
    public URL. Returns container id."""
    ig_id = _get("ig_user_id_env")
    tok = _get("ig_access_token_env")
    if not ig_id or not tok:
        return {"error": "missing IG_USER_ID / IG_ACCESS_TOKEN"}
    base = f"https://graph.facebook.com/v19.0/{ig_id}/media"
    if is_reel:
        payload = {"media_type": "REELS", "video_url": media_path_or_url,
                   "caption": caption, "access_token": tok}
    else:
        payload = {"image_url": media_path_or_url, "caption": caption, "access_token": tok}
    return _post(base, payload)


def publish_container(container_id):
    ig_id = _get("ig_user_id_env")
    tok = _get("ig_access_token_env")
    if not ig_id or not tok:
        return {"error": "missing creds"}
    url = f"https://graph.facebook.com/v19.0/{ig_id}/media_publish"
    return _post(url, {"creation_id": container_id, "access_token": tok})


def log_caption(caption, pillar, kind):
    logp = os.path.join(ROOT, CFG["instagram"]["caption_log"])
    import datetime
    with open(logp, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": str(datetime.datetime.now()), "pillar": pillar,
                            "kind": kind, "caption": caption}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    print("instagram_pub loaded. Set IG_USER_ID + IG_ACCESS_TOKEN to publish.")
