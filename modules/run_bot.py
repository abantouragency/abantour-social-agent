"""
run_bot.py — main orchestrator for AbanTour Social Agent.
Runs one cycle: plan -> scout trends -> (OpenAI) caption -> render reel + infographic
-> stage to private Telegram (approval) -> log. Then optionally publishes on approval.
Also a thin scheduler loop (every 60s) that triggers posting at configured slots.
"""
import os, sys, json, time, datetime, glob
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "modules"))
for m in ("text_rtl", "video_factory", "infographic_factory", "caption_engine",
          "content_planner", "trend_scout", "telegram_pub", "instagram_pub", "cleanup"):
    __import__(m)
import video_factory, infographic_factory, caption_engine, content_planner
import trend_scout, telegram_pub, instagram_pub, cleanup
import image_provider, video_factory_b, media_host
import cinematic_post, audio_mix, sora_provider

CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))


def _openai_key():
    return os.environ.get(CFG["openai"]["api_key_env"], "")


def produce_one(plan):
    pillar = next((p for p in CFG["content_pillars"] if p["id"] == plan["pillar"]), None)
    topic = plan["topic"]
    # trends enrich topic
    try:
        trends = trend_scout.scout()
        gt = trends.get("google_trends", {})
        flat = []
        for k, v in gt.items():
            if isinstance(v, list):
                flat += v
        if flat:
            topic = f"{topic} — ترند: {flat[0]}"
    except Exception:
        pass
    cap = caption_engine.generate(pillar, topic, _openai_key())
    # REEL (style B: scene-based, branded)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    from PIL import Image
    reel = os.path.join(ROOT, CFG["paths"]["output_reels"], f"reel_{plan['pillar']}_{ts}.mp4")
    # build 3 visual scenes from the topic + pillar
    scenes = _scenes_for(plan, topic)
    key = _openai_key()
    sora_cfg = CFG.get("sora", {})
    if key and sora_cfg.get("enabled"):
        # generate a single cinematic clip via Sora, then grade it
        prompt = _cinematic_prompt(plan, topic)
        res = sora_provider.generate(prompt, reel, api_key=key,
                                     duration=sora_cfg.get("duration", 10),
                                     size=sora_cfg.get("size", "1080x1920"))
        if isinstance(res, dict) and res.get("path"):
            reel = res["path"]
        else:
            video_factory_b.build(cap.get("hook", topic), cap.get("body", ""),
                                  cap.get("closing", ""), scenes, reel, api_key=key)
    else:
        video_factory_b.build(cap.get("hook", topic), cap.get("body", ""),
                              cap.get("closing", ""), scenes, reel, api_key=key)
    # --- cinematic post + audio ---
    music, voice = audio_mix.prepare(cap.get("hook"))
    graded = reel.replace(".mp4", "_cinematic.mp4")
    try:
        cinematic_post.grade(reel, graded, music_path=music, voice_path=voice,
                             letterbox=True, grain=10)
        if os.path.exists(graded) and os.path.getsize(graded) > 1000:
            reel = graded
    except Exception as e:
        print("cinematic_post skipped:", e)
    # INFOGRAPHIC
    info = os.path.join(ROOT, CFG["paths"]["output_infographics"], f"info_{plan['pillar']}_{ts}.png")
    infographic_factory.render(cap.get("hook", topic),
                               cap.get("body", "").split(". "),
                               cap.get("closing", ""), info,
                               meta={"pillar": plan["pillar"], "topic": topic,
                                     "hashtags": cap.get("hashtags", []),
                                     "meta_description": cap.get("meta_description", "")})
    # caption text for publishing
    full_caption = (f"{cap.get('hook','')}\n\n{cap.get('body','')}\n\n{cap.get('closing','')}\n\n"
                    + " ".join(cap.get("hashtags", [])))
    return {"reel": reel, "info": info, "caption": full_caption, "caption_data": cap, "plan": plan}


def stage_for_approval(item):
    priv = os.environ.get(CFG["telegram"]["private_channel_id_env"], "")
    if not priv:
        return {"staged": False, "reason": "no private channel id"}
    # send reel (video) + infographic (photo) to private channel
    r1 = telegram_pub.stage_private(priv, item["reel"], "🎬 ریلز (پیش‌نویس): " + item["caption"], kind="video")
    r2 = telegram_pub.stage_private(priv, item["info"], "🖼 اینفوگرافیک (پیش‌نویس): " + item["caption"], kind="photo")
    return {"staged": True, "reel_msg": r1.get("result", {}).get("message_id"),
            "info_msg": r2.get("result", {}).get("message_id")}


def cycle(slot=None):
    plans = content_planner.plan_day()
    if slot:
        plans = [p for p in plans if p["slot"] == slot]
    out = []
    for plan in plans:
        item = produce_one(plan)
        staged = stage_for_approval(item) if CFG["posting"]["approval_required"] else publish(item)
        out.append({"plan": plan, "staged": staged})
    return out


def _cinematic_prompt(plan, topic):
    """Build a Sora-ready cinematic prompt from the per-pillar prompt library."""
    try:
        data = json.load(open(os.path.join(ROOT, "assets/prompts_cinematic.json"),
                              encoding="utf-8"))
        lib = data.get("prompts", {}).get(plan["pillar"], [])
        base = lib[0] if lib else (plan["pillar"] + " travel scene")
        suffix = data.get("global_suffix", "")
        return f"{base}. {suffix} Theme: {topic}."
    except Exception:
        return f"cinematic 3D travel scene about {topic}, navy and gold palette, storybook style"


def _scenes_for(plan, topic):
    """Return 3 visual scene dicts {label, prompt} for the reel, based on pillar."""
    base = {
        "deals": [("تخفیف چارتر", f"discount flight tickets offer, {topic}"),
                  ("مقصد پرطرفدار", f"popular travel destination {topic}"),
                  ("مسافر خوشحال", "happy traveler at airport boarding")],
        "visa": [("ویزا", f"visa document and passport, {topic}"),
                 ("سفارتخانه", "embassy building exterior elegant"),
                 ("مسافر", "traveler checking passport happily")],
        "hotel": [("هتل لوکس", f"luxury hotel room view, {topic}"),
                  ("لابی", "elegant hotel lobby with gold accents"),
                  ("استخر", "resort pool at sunset")],
        "trend": [("مقصد ترند", f"trending travel destination {topic}"),
                  ("جاذبه", "famous landmark aerial view"),
                  ("طبیعت", "scenic nature landscape golden hour")],
        "tips": [("نکته سفر", f"travel tips illustration, {topic}"),
                 ("چمدان", "packed suitcase travel essentials"),
                 ("نقشه", "map and route planning")],
        "story": [("لحظه سفر", f"cinematic travel moment, {topic}"),
                  ("غروب", "beautiful sunset beach travel"),
                  ("خیابان", "charming old town street travel")],
    }
    return [{"label": l, "prompt": p} for l, p in base.get(plan["pillar"], base["tips"])]


def publish(item):
    # public telegram + instagram (after approval)
    pub = CFG["telegram"]["public_channel"]
    r1 = telegram_pub.publish_public(pub, item["reel"], item["caption"], kind="video")
    r2 = telegram_pub.publish_public(pub, item["info"], item["caption"], kind="photo")
    # Instagram: host reel publicly -> Graph API
    backend = CFG["media_host"]["backend"]
    public_url = media_host.upload(item["reel"], backend=backend)
    ig = {}
    if isinstance(public_url, str) and public_url.startswith("http"):
        ig = instagram_pub.create_container(public_url, item["caption"], is_reel=True)
    instagram_pub.log_caption(item["caption"], item["plan"]["pillar"], "reel")
    return {"telegram": [r1.get("ok"), r2.get("ok")],
            "instagram": ig, "ig_url": public_url}


def scheduler_loop():
    """Background loop: at each configured slot, run cycle(); then cleanup."""
    print("Scheduler started. Slots:", [(s["slot"], s["hour"], s["minute"]) for s in CFG["posting"]["daily_slots"]])
    last = set()
    while True:
        now = datetime.datetime.now()
        key = (now.hour, now.minute // 1)
        for s in CFG["posting"]["daily_slots"]:
            sk = (s["hour"], s["minute"])
            if now.hour == s["hour"] and now.minute == s["minute"] and sk not in last:
                print(f"[{now}] firing slot {s['slot']}")
                try:
                    cycle(s["slot"])
                except Exception as e:
                    print("cycle error:", e)
                last.add(sk)
        # reset last at midnight
        if now.hour == 0 and now.minute == 0:
            last.clear()
        time.sleep(30)
        cleanup.run()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", help="run one slot: morning|evening")
    ap.add_argument("--schedule", action="store_true", help="run forever scheduler")
    ap.add_argument("--test", action="store_true", help="produce one sample item locally")
    a = ap.parse_args()
    if a.test:
        item = produce_one(content_planner.pick("morning"))
        print("TEST produced:", json.dumps({k: (v if k != "caption_data" else v.get("source"))
                                            for k, v in item.items()}, ensure_ascii=False, indent=2))
    elif a.slot:
        print(json.dumps(cycle(a.slot), ensure_ascii=False, indent=2)[:2000])
    elif a.schedule:
        scheduler_loop()
    else:
        print("Use --test | --slot morning|evening | --schedule")
