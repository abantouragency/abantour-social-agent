"""
video_factory.py — Style A: branded motion text reels (no GPU, ffmpeg based).

Produces a 1080x1920 (9:16) vertical short (~20s) from:
  - a hook (top, gold)
  - a body (middle, white, multi-line)
  - a closing/CTA (bottom)
  - animated background (navy gradient + drifting gold particles)
  - AbanTour logo overlay + wordmark

Frames are rendered with PIL, encoded with ffmpeg into mp4 (H.264, AAC).
"""
import os, json, math, random, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont
import text_rtl as rtl
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
BRAND = CFG["brand"]
W, H = 1080, 1920
FPS = 30
DURATION = 15


def _font(size, bold=True):
    rel = BRAND["font_bold"] if bold else BRAND["font_regular"]
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    return ImageFont.truetype(p, size)


def _draw_text_block(d, cx, top, lines, font, fill):
    lh = font.size * 1.35
    y = top
    for ln in lines:
        d.text((cx, y), ln, font=font, fill=fill, anchor="mm")
        y += lh
    return y


def _background(frame_idx, total_frames):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    # vertical navy gradient
    for y in range(H):
        t = y / H
        r = int(0x0B + (0x07 - 0x0B) * t)
        g = int(0x1F + (0x14 - 0x1F) * t)
        b = int(0x3A + (0x2B - 0x3A) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    # drifting gold particles
    t = frame_idx / total_frames
    random.seed(7)
    for i in range(26):
        px = (random.randint(0, W) + int(t * (60 + i * 9))) % W
        py = (random.randint(0, H) + int(t * (40 + i * 7))) % H
        rad = random.randint(2, 6)
        a = random.randint(40, 150)
        d.ellipse([px - rad, py - rad, px + rad, py + rad], fill=(212, 175, 55, a))
    return img


def _logo():
    lp = BRAND["logo"]
    if os.path.exists(lp):
        lg = Image.open(lp).convert("RGBA")
        lg = lg.resize((300, 100))
        return lg
    return None


def render(hook: str, body: str, closing: str, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp_frames = tempfile.mkdtemp(prefix="vf_", dir=os.path.join(ROOT, "tmp"))
    total = FPS * DURATION
    f_hook = _font(64)
    f_body = _font(48, bold=False)
    f_cls = _font(40)
    logo = _logo()

    for fi in range(total):
        img = _background(fi, total)
        d = ImageDraw.Draw(img, "RGBA")
        # hook in gold box
        hook_lines = rtl.fit_lines(hook, max_chars=18, max_lines=3)
        # subtle panel behind hook
        d.rectangle([40, 120, W - 40, 120 + len(hook_lines) * f_hook.size * 1.4 + 40],
                    fill=(212, 175, 55, 30))
        _draw_text_block(d, W / 2, 200, hook_lines, f_hook, "#E8C766")
        # body
        body_lines = rtl.fit_lines(body, max_chars=20, max_lines=5)
        _draw_text_block(d, W / 2, H / 2 - 80, body_lines, f_body, "#F5F7FA")
        # closing
        cls_lines = rtl.fit_lines(closing, max_chars=22, max_lines=2)
        _draw_text_block(d, W / 2, H - 260, cls_lines, f_cls, "#D4AF37")

        # fade-in logo near top
        if logo and fi < total * 0.85:
            alpha = min(1.0, fi / (FPS * 1.5))
            lg = logo.copy()
            lg.putalpha(int(255 * alpha))
            img.paste(lg, (W // 2 - 150, 40), lg)

        # progress bar (gold) at bottom
        p = fi / total
        d.rectangle([0, H - 12, int(W * p), H - 4], fill="#D4AF37")

        fr = os.path.join(tmp_frames, f"f_{fi:05d}.png")
        img.save(fr)

    # encode
    pattern = os.path.join(tmp_frames, "f_%05d.png")
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", pattern,
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-movflags", "+faststart", out_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path


if __name__ == "__main__":
    sample = os.path.join(ROOT, "output/reels/sample_reel.mp4")
    render("قیمت امروز استانبول سقوط کرد! 👇",
           "چارتر مستقیم با کمترین قیمت فصل. فقط این هفته، صندلی محدود.",
           "📩 ۰۲۱-۵۵۰۰۹۴۲۹  |  @abantour_agency",
           sample)
    print("REEL ->", sample)
