"""
content_planner.py — picks pillar + topic per slot, builds a content calendar,
avoids repeats, and logs to data/calendar.jsonl.
"""
import os, json, sys, random, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
CAL = os.path.join(ROOT, "data/calendar.jsonl")
SLOTS = CFG["posting"]["daily_slots"]


def _weighted_pillar():
    pillars = CFG["content_pillars"]
    pool = []
    for p in pillars:
        pool += [p] * int(p.get("weight", 1))
    return random.choice(pool)


_TOPICS = {
    "deals": ["تخفیف‌های چارتر استانبول", "ارزان‌ترین پرواز دبی", "قیمت لحظه‌ای آنتالیا", "بلیط سیستمی اروپا"],
    "visa": ["ویزای ترکیه", "ویزای شنگن", "ویزای دبی", "مدارک ویزای گرجستان"],
    "hotel": ["هتل ارزان استانبول", "اقامت در باکو", "رزرو هتل دبی", "بهترین ریزورت آنتالیا"],
    "trend": ["مقصد ترند پاییز", "سفر ارزان نوروز", "جزایر مدیرترند", "تورهای اروپایی امسال"],
    "tips": ["۵ اشتباه خرید بلیط", "بار مجاز هواپیما", "چطور ارزان سفر کنیم", "زمان مناسب رزرو"],
    "story": ["سفر به یادماندنی به کوش آداسی", "تجربه مسافران از آنتالیا", "اولین سفر خارجی", "لحظه‌های سفر"]
}


def pick(slot_name: str, date=None):
    date = date or datetime.date.today()
    pillar = _weighted_pillar()
    topic = random.choice(_TOPICS.get(pillar["id"], ["سفر"]))
    return {"date": str(date), "slot": slot_name, "pillar": pillar["id"],
            "pillar_name": pillar["name"], "emoji": pillar.get("emoji", ""),
            "topic": topic, "status": "planned"}


def plan_day(date=None):
    return [pick(s["slot"], date) for s in SLOTS]


def log_plan(plans):
    os.makedirs(os.path.dirname(CAL), exist_ok=True)
    with open(CAL, "a", encoding="utf-8") as f:
        for p in plans:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    return plans


if __name__ == "__main__":
    plans = log_plan(plan_day())
    print(json.dumps(plans, ensure_ascii=False, indent=2))
