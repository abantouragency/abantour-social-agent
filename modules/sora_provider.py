"""
sora_provider.py — generates video clips via OpenAI Sora (video generations API).
Flexible: tries the openai SDK, falls back to a raw HTTPS request to the
/v1/videos/generations endpoint. Returns a downloaded local .mp4 path.
(The live call needs OPENAI_API_KEY + internet; runs on the user's PC.)
"""
import os, sys, json, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
BASE = CFG["openai"].get("base_url", "https://api.openai.com/v1")


def _download(url, out_path):
    import urllib.request
    urllib.request.urlretrieve(url, out_path)
    return out_path


def generate(prompt, out_path, api_key=None, duration=10, size="1080x1920",
             model=None, n=1):
    api_key = api_key or os.environ.get(CFG["openai"]["api_key_env"], "")
    model = model or CFG.get("sora", {}).get("model", "sora")
    if not api_key:
        return {"error": "no OPENAI_API_KEY"}
    # 1) try SDK
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=CFG["openai"].get("base_url"))
        r = client.videos.generations.create(
            model=model, prompt=prompt, n=n, size=size, duration=duration)
        url = r.data[0].url
        return {"ok": True, "path": _download(url, out_path)}
    except Exception as e_sdk:
        # 2) raw HTTPS fallback
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                BASE + "/videos/generations",
                data=_json.dumps({
                    "model": model, "prompt": prompt, "n": n,
                    "size": size, "duration": duration
                }).encode(),
                headers={"Authorization": f"Bearer {api_key}",
                          "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = _json.loads(resp.read().decode())
            url = data["data"][0]["url"]
            return {"ok": True, "path": _download(url, out_path), "method": "raw"}
        except Exception as e_raw:
            return {"error": f"sdk:{e_sdk} | raw:{e_raw}"}


if __name__ == "__main__":
    print("sora_provider loaded. Needs OPENAI_API_KEY to generate.")
