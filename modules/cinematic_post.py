"""
cinematic_post.py — post-process a reel into a cinematic, on-brand (navy+gold)
look:
  - thin letterbox bars (film feel)
  - navy/gold color grade + subtle vignette + film grain
  - optional royalty-free background music + optional Farsi voice hook
  - branded lower-third is baked by the caller (video_factory_b)
Works fully offline (ffmpeg only) -> TESTABLE in the sandbox.
"""
import os, sys, subprocess, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config/settings.json"), encoding="utf-8"))
BRAND = CFG["brand"]


def grade(input_path, output_path, music_path=None, voice_path=None,
         letterbox=True, grain=12):
    cmd = ["ffmpeg", "-y", "-i", input_path]
    ainputs = 1
    af = []
    # audio inputs
    if music_path and os.path.exists(music_path):
        cmd += ["-i", music_path]; ainputs += 1
        af.append(f"[{ainputs-1}:a]volume=0.22[mus]")
    if voice_path and os.path.exists(voice_path):
        cmd += ["-i", voice_path]; ainputs += 1
        af.append(f"[{ainputs-1}:a]volume=1.0[vc]")
    # ---- video filter chain ----
    vf = []
    if letterbox:
        vf.append("drawbox=x=0:y=0:w=iw:h=90:color=black@1:t=fill")
        vf.append("drawbox=x=0:y=ih-90:w=iw:h=90:color=black@1:t=fill")
    # navy shadows + gold highlights grade (values 0..1)
    vf.append("colorbalance=rs=0.92:gs=0.96:bs=1.00:rm=1.00:gm=0.98:bm=0.85")
    vf.append("hue=s=1.10")
    vf.append("vignette=PI/4.2")
    if grain and grain > 0:
        vf.append(f"noise=alls={grain}:allf=t")
    vfilter = ",".join(vf)
    # ---- audio mix ----
    if af:
        labels = [a[a.rfind("[")+1:a.rfind("]")] for a in af]  # mus / vc
        if len(labels) == 1:
            # single audio source: keep its volume filter, map it directly
            afilter = ";".join(af)
            cmd += ["-filter_complex", f"[0:v]{vfilter}[vout];{afilter}",
                    "-map", "[vout]", "-map", f"[{labels[0]}]"]
        else:
            amap = "+".join(f"[{l}]" for l in labels) + f"amix=inputs={len(labels)}:duration=first:dropout_transition=0[aout]"
            afilter = ";".join(af) + ";" + amap
            cmd += ["-filter_complex", f"[0:v]{vfilter}[vout];{afilter}",
                    "-map", "[vout]", "-map", "[aout]"]
    else:
        cmd += ["-vf", vfilter]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", "-shortest", output_path]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


if __name__ == "__main__":
    print("cinematic_post loaded.")
