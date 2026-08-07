"""Generate the AbanTour brand logo (navy disk + gold plane + wordmark)."""
from PIL import Image, ImageDraw, ImageFont
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_B = os.path.join(ROOT, "assets/fonts/Vazirmatn-Bold.ttf")
OUT = os.path.join(ROOT, "assets/templates/logo.png")
if not os.path.isabs(FONT_B):
    FONT_B = os.path.join(ROOT, FONT_B)

def render_text(draw, xy, text, font, fill, anchor="mm"):
    try:
        from bidi.algorithm import get_display
        import arabic_reshaper
        text = get_display(arabic_reshaper.reshape(text))
    except Exception:
        pass
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)

def main():
    W, H = 600, 200
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # navy rounded plate
    d.rounded_rectangle([10, 30, W-10, H-30], radius=28, fill="#0B1F3A")
    # gold ring
    d.ellipse([30, 50, 130, 150], outline="#D4AF37", width=5)
    # simple plane glyph in gold
    d.line([80, 100, 110, 100], fill="#D4AF37", width=5)
    d.polygon([(110, 100), (98, 92), (98, 108)], fill="#D4AF37")
    d.line([82, 100, 70, 84], fill="#D4AF37", width=3)
    d.line([82, 100, 70, 116], fill="#D4AF37", width=3)
    # wordmark
    f = ImageFont.truetype(FONT_B, 44)
    render_text(d, (250, 88), "آبان تور", f, "#F5F7FA")
    f2 = ImageFont.truetype(FONT_B, 20)
    render_text(d, (250, 128), "ABAN TOUR • سفر با خیال آسوده", f2, "#E8C766")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("logo ->", OUT)

if __name__ == "__main__":
    main()
