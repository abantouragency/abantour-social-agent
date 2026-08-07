"""
image_provider.py — supplies one themed image per scene.
Backends:
  - "dalle": OpenAI DALL-E (used once OPENAI_API_KEY is provided)
  - "local": branded gradient placeholder with scene label (fallback / testing)
Switch automatically: if api_key present -> dalle, else local.
"""
import os, sys, json, random
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
BRAND = CFG["brand"]
ASSETS = os.path.join(ROOT, "assets")


def _font(size, bold=True):
    rel = BRAND["font_bold"] if bold else BRAND["font_regular"]
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    return ImageFont.truetype(p, size)


def _local_image(scene_label, idx, out_path, palette=("navy", "gold")):
    """Branded gradient placeholder so style-B can be tested without DALL-E."""
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    base = (11, 31, 58) if palette[0] == "navy" else (7, 20, 43)
    for y in range(H):
        t = y / H
        r = int(base[0] * (1 - t) + 30 * t)
        g = int(base[1] * (1 - t) + 24 * t)
        b = int(base[2] * (1 - t) + 55 * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    # big faint scene number + icon circle (gold)
    d.ellipse([W/2 - 220, H/2 - 380, W/2 + 220, H/2 - 60], outline="#D4AF37", width=8)
    f = _font(360, bold=True)
    d.text((W/2, H/2 - 220), str(idx + 1), font=f, fill=(212, 175, 55, 90), anchor="mm")
    # scene label at bottom
    f2 = _font(56, bold=True)
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        label = get_display(arabic_reshaper.reshape(scene_label))
    except Exception:
        label = scene_label
    d.text((W/2, H - 320), label, font=f2, fill="#E8C766", anchor="mm")
    img.save(out_path)
    return out_path


def _dalle_image(prompt, out_path, api_key):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=CFG["openai"].get("base_url"))
    resp = client.images.generate(
        model="dall-e-3", prompt=prompt,
        size="1024x1792", quality="standard", n=1)
    url = resp.data[0].url
    import urllib.request
    urllib.request.urlretrieve(url, out_path)
    return out_path


def get_image(scene_label, idx, out_path, api_key=None, prompt_hint=None):
    api_key = api_key or os.environ.get(CFG["openai"]["api_key_env"], "")
    if api_key:
        # Build a brand-consistent DALL-E prompt
        base = ("Cinematic travel photograph, professional, high detail, "
                "navy and gold color palette, elegant, no text, "
                "AbanTour travel agency style. Scene: ")
        p = base + (prompt_hint or scene_label)
        try:
            return _dalle_image(p, out_path, api_key)
        except Exception as e:
            print("DALL-E failed, local fallback:", e)
    return _local_image(scene_label, idx, out_path)


if __name__ == "__main__":
    out = os.path.join(ROOT, "tmp", "scene_test.png")
    print(get_image("ویزای ترکیه", 0, out))
