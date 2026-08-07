"""cleanup.py — removes tmp/ every run, trims stale published/logs by age."""
import os, json, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))


def clean_tmp():
    tmp = os.path.join(ROOT, "tmp")
    n = 0
    for f in os.listdir(tmp) if os.path.isdir(tmp) else []:
        if f in ("reel_test.py",):  # keep helper
            continue
        p = os.path.join(tmp, f)
        try:
            if os.path.isfile(p):
                os.remove(p); n += 1
            elif os.path.isdir(p):
                import shutil; shutil.rmtree(p); n += 1
        except Exception:
            pass
    return n


def trim_old(folder_key, days):
    folder = os.path.join(ROOT, CFG["paths"][folder_key])
    if not os.path.isdir(folder):
        return 0
    cutoff = time.time() - days * 86400
    n = 0
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        try:
            if os.path.isfile(p) and os.path.getmtime(p) < cutoff:
                os.remove(p); n += 1
        except Exception:
            pass
    return n


def run():
    r = {"tmp_removed": 0, "published_trimmed": 0, "logs_trimmed": 0}
    if CFG["cleanup"]["tmp_every_run"]:
        r["tmp_removed"] = clean_tmp()
    r["published_trimmed"] = trim_old("published", CFG["cleanup"]["keep_published_days"])
    r["logs_trimmed"] = trim_old("logs", CFG["cleanup"]["keep_logs_days"])
    return r


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
