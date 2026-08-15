"""
pc_producer.py — runs on your Windows PC. Produces heavy content locally
(style B reel + infographic + cinematic grade), uploads media to the public
host (catbox/R2/FTP), then stages the result to the Render orchestrator via
the web API. Controlled by the same content_planner schedule.
"""
import os, sys, json, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "modules"))
import run_bot, video_factory_b, media_host, state_db  # state_db only for local staging backup
from flask import Flask  # noqa (avoid name clash on some setups)

RENDER_BASE = os.environ.get("RENDER_BASE", "")
STAGE_TOKEN = os.environ.get("STAGE_TOKEN", "")


def produce_and_stage(slot):
    """Produce one item for the given slot, upload, and stage to Render."""
    plan = run_bot.content_planner.pick(slot)
    item = run_bot.produce_one(plan)
    # upload media to public host
    reel_url = media_host.upload(item["reel"]) if os.path.exists(item["reel"]) else None
    info_url = media_host.upload(item["info"]) if os.path.exists(item["info"]) else None
    if not reel_url and not info_url:
        raise RuntimeError("media host upload failed (no public URL)")
    rec = {
        "id": f"{plan['pillar']}_{slot}_{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
        "pillar": plan["pillar"],
        "slot": slot,
        "topic": item["topic"],
        "reel_url": reel_url or "",
        "info_url": info_url or "",
        "caption": item["caption"],
        "hook": item["hook"],
        "platforms": ["telegram", "instagram"],
    }
    # stage to Render (primary) + local backup
    state_db.add_item({**rec, "status": "staged"})
    if RENDER_BASE and STAGE_TOKEN:
        import urllib.request
        req = urllib.request.Request(
            f"{RENDER_BASE}/api/stage",
            data=json.dumps(rec).encode(),
            headers={"Content-Type": "application/json", "X-Stage-Token": STAGE_TOKEN},
            method="POST")
        urllib.request.urlopen(req, timeout=60)
    return rec


def run_slot(slot):
    try:
        rec = produce_and_stage(slot)
        print(f"[PC] staged {rec['id']} -> reel={bool(rec['reel_url'])} info={bool(rec['info_url'])}")
        return rec
    except Exception as e:
        print(f"[PC] ERROR {slot}: {e}")
        raise


def watch(interval=30):
    """Watchdog: pull /now requests from Render and produce them. Runs forever on PC."""
    import time, urllib.request
    print(f"[PC] watchdog started (poll every {interval}s)")
    while True:
        try:
            if RENDER_BASE and STAGE_TOKEN:
                req = urllib.request.Request(
                    f"{RENDER_BASE}/api/pc_requests",
                    headers={"X-Stage-Token": STAGE_TOKEN}, method="GET")
                data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
                for r in data.get("requests", []):
                    pillar = r.get("pillar", "deals")
                    print(f"[PC] producing requested pillar: {pillar}")
                    produce_and_stage(_slot_for_pillar(pillar))
            else:
                print("[PC] RENDER_BASE/STAGE_TOKEN not set; skipping remote poll")
        except Exception as e:
            print(f"[PC] watchdog poll error: {e}")
        time.sleep(interval)


def _slot_for_pillar(pillar):
    # map pillar to a slot name; default to a time-based slot
    h = datetime.datetime.now().hour
    return "morning" if h < 15 else "evening"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        watch()
    else:
        slots = sys.argv[1:] or ["morning", "evening"]
        for s in slots:
            run_slot(s)
