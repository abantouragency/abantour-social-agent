"""
video_factory_b.py — STYLE B: scene-based motion reel.
Each scene = one image (from image_provider) with a Ken Burns (zoompan) effect,
cross-faded (xfade) into the next, branded lower-third + logo stinger + animated
hook text overlay. Produces 1080x1920 9:16 reel via ffmpeg.
"""
import os, sys, json, subprocess, tempfile, math
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
BRAND = CFG["brand"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import text_rtl as rtl
import image_provider as ip

W, H = 1080, 1920
SCENE_SEC = 3.5        # seconds per scene
TRANS_SEC = 0.6        # crossfade duration
FPS = 30


def _font(size, bold=True):
    rel = BRAND["font_bold"] if bold else BRAND["font_regular"]
    p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
    return ImageFont.truetype(p, size)


def build(hook, body, closing, scenes, out_path, api_key=None):
    """
    scenes: list of dicts {label, prompt} describing each visual scene.
    Returns out_path.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="vb_", dir=os.path.join(ROOT, "tmp"))
    n = max(2, len(scenes))

    # 1) generate scene images
    scene_imgs = []
    for i, sc in enumerate(scenes[:n]):
        sp = os.path.join(tmp, f"scene_{i}.png")
        ip.get_image(sc.get("label", f"صحنه {i+1}"), i, sp,
                     api_key=api_key, prompt_hint=sc.get("prompt"))
        _bake_branding(sp, sc.get("label", f"صحنه {i+1}"))
        scene_imgs.append(sp)

    # 2) make a Ken Burns clip per scene (zoompan) + lower-third branding
    clips = []
    for i, sp in enumerate(scene_imgs):
        cp = os.path.join(tmp, f"clip_{i}.mp4")
        _make_kb_clip(sp, i, cp)
        clips.append(cp)

    # 3) concat with xfade transitions
    pattern = os.path.join(tmp, "clip_%d.mp4")
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    # build filter_complex: chain xfade (offset in SECONDS)
    off = SCENE_SEC - TRANS_SEC
    fc = f"[0:v][1:v]xfade=transition=fade:duration={TRANS_SEC}:offset={off:.2f}[v1];"
    for i in range(2, len(clips)):
        fc += f"[v{i-1}][{i}:v]xfade=transition=fade:duration={TRANS_SEC}:offset={off:.2f}[v{i}];"
    fc = fc.rstrip(";")
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", fc,
          "-map", f"[v{len(clips)-1}]", "-c:v", "libx264", "-preset", "veryfast",
          "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 4) overlay hook text + logo stinger on top
    final = out_path.replace(".mp4", "_branded.mp4")
    _overlay_brand(out_path, hook, closing, final)
    os.replace(final, out_path)
    return out_path


def _make_kb_clip(img_path, idx, out_path):
    # Ken Burns: loop still image to a timed stream, scale up, slow pan via
    # time-based crop. Branding is baked into the base image (PIL) so we avoid
    # the overlay 'shortest=1' trap that truncates the clip to 1 frame.
    cmd = [
        "ffmpeg", "-y", "-i", img_path,
        "-filter_complex",
        f"[0:v]loop=loop={int(SCENE_SEC*FPS)-1}:size=1:start=0,"
        f"scale={int(W*1.12)}:{int(H*1.12)},"
        f"crop={W}:{H}:'({W*1.12}-{W})*t/{SCENE_SEC}':'({H*1.12}-{H})*t/{SCENE_SEC}',"
        f"format=yuv420p[vout]",
        "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast",
        "-t", str(SCENE_SEC), "-pix_fmt", "yuv420p", "-r", str(FPS), out_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _bake_branding(img_path, label):
    """Add lower-third brand bar + scene label onto the base image (PIL)."""
    img = Image.open(img_path).convert("RGBA")
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 300, W, H], fill=(7, 20, 43, 235))
    d.rectangle([0, H - 300, W, H - 292], fill="#D4AF37")
    f = _font(44, bold=True)
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        label = get_display(arabic_reshaper.reshape(label))
    except Exception:
        pass
    d.text((60, H - 150), "✈  آبان تور  |  " + label, font=f,
           fill="#E8C766", anchor="lm")
    img.convert("RGB").save(img_path)


def _draw_lower_third(out_path):
    img = Image.new("RGBA", (W, 300), (7, 20, 43, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill="#D4AF37")
    f = _font(44, bold=True)
    d.text((60, 150), "✈  آبان تور  |  سفر با خیال آسوده", font=f,
           fill="#E8C766", anchor="lm")
    img.save(out_path)


def _overlay_brand(video_path, hook, closing, out_path):
    # text overlay via drawtext is complex with RTL; use PIL-baked PNG frames instead
    tmp = tempfile.mkdtemp(prefix="ov_", dir=os.path.join(ROOT, "tmp"))
    hook_png = os.path.join(tmp, "hook.png")
    _draw_hook(hook_png, hook)
    close_png = os.path.join(tmp, "close.png")
    _draw_close(close_png, closing)
    # top hook overlay at start (first 3s), closing near end
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", hook_png, "-i", close_png,
        "-filter_complex",
        f"[1:v]format=yuva420p,fade=t=in:st=0.3:d=0.5,fade=t=out:st=3.0:d=0.5[ht];"
        f"[2:v]format=yuva420p,fade=t=in:st=0.3:d=0.5[ct];"
        f"[0:v][ht]overlay=40:80:enable='between(t,0,4)'[v1];"
        f"[v1][ct]overlay=40:{H-200}:enable='gte(t,4)'[vout]",
        "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _draw_hook(out_path, text):
    img = Image.new("RGBA", (W - 80, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 80, 400], fill=(212, 175, 55, 55))
    f = _font(56, bold=True)
    for i, ln in enumerate(rtl.fit_lines(text, 16, 4)):
        d.text((40, 60 + i * 70), ln, font=f, fill="#FFF6E0", anchor="la")
    img.save(out_path)


def _draw_close(out_path, text):
    img = Image.new("RGBA", (W - 80, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font(38, bold=True)
    for i, ln in enumerate(rtl.fit_lines(text, 26, 3)):
        d.text((40, 20 + i * 52), ln, font=f, fill="#E8C766", anchor="la")
    img.save(out_path)


if __name__ == "__main__":
    out = os.path.join(ROOT, "output/reels", "sample_styleB.mp4")
    scenes = [
        {"label": "ویزای ترکیه", "prompt": "Istanbul Bosphorus bridge at sunset, travelers"},
        {"label": "هتل لوکس", "prompt": "luxury hotel room with city view, elegant"},
        {"label": "پرواز", "prompt": "airplane window view above clouds at golden hour"},
    ]
    build("ویزای ترکیه از این هفته راحت‌تر شد 🛂",
          "", "📩 ۰۲۱-۵۵۰۰۹۴۲۹  •  @abantour_agency",
          scenes, out)
    print("STYLE B ->", out)
