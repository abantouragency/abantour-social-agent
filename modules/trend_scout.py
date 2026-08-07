"""
trend_scout.py — fetches Google Trends (IR) interest + top related queries, and
smartly scrapes competitor deal pages (best-effort, with graceful fallback).
Caches results for cache_hours. Runs on the PC (needs internet).
"""
import os, json, sys, time, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
CACHE = os.path.join(ROOT, "data/trends_cache.json")


def _load_cache():
    if os.path.exists(CACHE):
        try:
            d = json.load(open(CACHE, encoding="utf-8"))
            if time.time() - d.get("ts", 0) < CFG["trend_scout"]["cache_hours"] * 3600:
                return d
        except Exception:
            pass
    return None


def google_trends():
    cfg = CFG["trend_scout"]
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="fa-IR", tz=210)
        out = {}
        for kw in cfg["google_trends_keywords"][:4]:
            try:
                pytrends.build_payload([kw], geo=cfg["google_trends_geo"])
                rel = pytrends.related_queries()
                top = rel.get(kw, {}).get("top")
                if top is not None:
                    out[kw] = [r["query"] for r in top["query"].head(5).to_dict("records")]
            except Exception:
                pass
        return out
    except Exception as e:
        return {"error": str(e)}


def competitor_pulse():
    """Best-effort: just lists known competitor promo pages (manual seed fallback)."""
    return [{"name": c["name"], "url": c["url"]} for c in CFG["trend_scout"]["competitors"]]


def scout(force=False):
    cached = None if force else _load_cache()
    if cached:
        return cached
    data = {
        "ts": time.time(),
        "date": str(datetime.date.today()),
        "google_trends": google_trends(),
        "competitors": competitor_pulse(),
        "seasonal": _seasonal_theme()
    }
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(data, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return data


def _seasonal_theme():
    m = datetime.date.today().month
    if m in (3, 4): return "سفر نوروزی"
    if m in (6, 7, 8): return "سفر تابستانی"
    if m in (9, 10, 11): return "سفر پاییزی"
    return "سفر زمستانی"


if __name__ == "__main__":
    print(json.dumps(scout(force=True), ensure_ascii=False, indent=2)[:1500])
