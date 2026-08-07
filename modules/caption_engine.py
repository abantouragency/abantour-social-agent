"""
caption_engine.py — uses OpenAI to write hook + body + closing + hashtags + meta
for a given pillar/topic. Falls back to local templates if no API key.
"""
import os, json, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
ASSETS = os.path.join(ROOT, "assets")


def _load(name):
    return json.load(open(os.path.join(ASSETS, name), encoding="utf-8"))


def _fallback(pillar, topic):
    hooks = _load("hooks.json")["hook_library"]
    hook = random.choice(hooks).replace("{dest}", topic)
    closings = _load("hooks.json")["closing_library"]
    hsh = _load("hashtags.json")
    hashtags = list(dict.fromkeys(
        hsh["broad_fa"][:3] + hsh["niche_fa"][:4] + hsh["brand"][:2] + hsh["broad_en"][:2]))
    return {
        "hook": hook,
        "body": f"در این پست درباره {topic} نکات کاربردی می‌خوانید. همراه آبان تور سفری هوشمندانه داشته باشید.",
        "closing": " | ".join(closings[:2]),
        "hashtags": hashtags,
        "meta_description": f"راهنمای {topic} توسط آژانس هواپیمایی آبان تور.",
        "source": "local_template"
    }


def generate(pillar: dict, topic: str, openai_key: str = None):
    if not openai_key:
        return _fallback(pillar["name"], topic)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key, base_url=CFG["openai"].get("base_url"))
        hsh = _load("hashtags.json")
        prompt = f"""شما کپی‌رایتر ارشد یک آژانس مسافرتی ایرانی (آبان تور) هستید.
ستون محتوا: {pillar['name']}. موضوع: {topic}.
یک پست اینستاگرام/تلگرام بنویسید با:
- قلاب (hook) کوتاه و جذاب حداکثر ۱۲ کلمه (فارسی)
- بدنه ۲ تا ۳ جمله کاربردی (فارسی، محاوره‌ای)
- بستار (closing) شامل کلیدواژه برند: @abantour_agency و تلفن ۰۲۱-۵۵۰۰۹۴۲۹
- ۱۰ تا ۱۳ هشتگ مرتبط (ترکیب فارسی و انگلیسی و برند)
- متا‌توضیحات (meta_description) یک جمله‌ای برای سئو
فرمت خروجی دقیقاً JSON با کلیدهای: hook, body, closing, hashtags (آرایه), meta_description."""
        r = client.chat.completions.create(
            model=CFG["openai"]["model"],
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, temperature=0.8)
        data = json.loads(r.choices[0].message.content)
        data["source"] = "openai"
        return data
    except Exception as e:
        fb = _fallback(pillar["name"], topic)
        fb["error"] = str(e)
        return fb
