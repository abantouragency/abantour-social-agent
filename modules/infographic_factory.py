"""
infographic_factory.py — topic infographic (1080x1350, Instagram portrait)
with branded frame, hook title, body bullets, footer CTA, and hashtag/meta baked
into a sidecar JSON for the publisher.
"""
import os, json, sys
from PIL import Image, ImageDraw, ImageFont
import text_rtl as rtl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
BRAND = CFG["brand"]
W, H = 1080, 1350


def _font(size, bold=True):
    rel = BRAND["font_bold"] if bold else BRAND["font_regular"]
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    return ImageFont.truetype(p, size)


def _shape(text):
    return rtl.shape(text)


def render(title: str, bullets: list, closing: str, out_path: str, meta: dict = None):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img = Image.new("RGB", (W, H), "#0B1F3A")
    d = ImageDraw.Draw(img, "RGBA")
    # top gold band + logo slot
    d.rectangle([0, 0, W, 150], fill="#07142B")
    d.rectangle([0, 150, W, 168], fill="#D4AF37")
    # title
    f_title = _font(58)
    for i, ln in enumerate(rtl.fit_lines(title, 16, 3)):
        d.text((W/2, 75 + i*70), ln, font=f_title, fill="#E8C766", anchor="mm")
    # body bullets in white card
    d.rounded_rectangle([60, 220, W-60, H-260], radius=24, fill="#F5F7FA")
    f_b = _font(40, bold=False)
    y = 300
    for b in bullets[:6]:
        lines = rtl.fit_lines("• " + b, 24, 3)
        for ln in lines:
            d.text((90, y), ln, font=f_b, fill="#0B1F3A", anchor="lm")
            y += 52
        y += 18
    # footer CTA band
    d.rectangle([0, H-200, W, H], fill="#07142B")
    f_c = _font(36)
    for i, ln in enumerate(rtl.fit_lines(closing, 26, 3)):
        d.text((W/2, H-150 + i*48), ln, font=f_c, fill="#D4AF37", anchor="mm")
    # logo
    lp = BRAND["logo"]
    if os.path.exists(lp):
        lg = Image.open(lp).convert("RGBA").resize((240, 80))
        img.paste(lg, (W//2 - 120, 60), lg)
    img.save(out_path)

    # sidecar meta for publisher
    if meta:
        side = out_path.rsplit(".", 1)[0] + ".meta.json"
        json.dump(meta, open(side, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return out_path


if __name__ == "__main__":
    out = os.path.join(ROOT, "output/infographics/sample_info.png")
    render(
        "۵ اشتباه رایج در خرید بلیط خارجی",
        ["فقط یک سایت چک کردن و قیمت را نهایی کردن",
         "نادیده گرفتن نرخ چارتر در ساعات شلوغ",
         "فراموشی هزینه بار اضافه",
         "ثبت‌نام دیرهنگام ویزا",
         "عدم مقایسه پروازهای غیرمستقیم"],
        "📩 ۰۲۱-۵۵۰۰۹۴۲۹  •  @abantour_agency",
        out,
        meta={"pillar": "tips", "hashtags": ["#بلیط_هواپیما", "#آبان_تور", "#سفر_خارجی"],
              "meta_description": "پنج اشتباه پرهزینه در خرید بلیط خارجی که مسافران تکرار می‌کنند."}
    )
    print("INFO ->", out)
