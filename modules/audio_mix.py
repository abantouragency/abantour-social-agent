"""
audio_mix.py — adds royalty-free background music + an optional Farsi voice hook.
Music: bundled ambient track is preferred; otherwise user drops files into
assets/audio/. Voice: optional TTS (e.g. Edge) — if unavailable, skipped silently.
Offline-capable with ffmpeg once the audio files exist.
"""
import os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_AUDIO = os.path.join(ROOT, "assets/audio")


def _find_music():
    if not os.path.isdir(ASSETS_AUDIO):
        return None
    for fn in os.listdir(ASSETS_AUDIO):
        if fn.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")) and "music" in fn.lower():
            return os.path.join(ASSETS_AUDIO, fn)
    # any audio
    for fn in os.listdir(ASSETS_AUDIO):
        if fn.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")):
            return os.path.join(ASSETS_AUDIO, fn)
    return None


def make_voice_hook(text, out_path):
    """Best-effort Farsi TTS via edge-tts (if installed). Returns path or None."""
    try:
        import edge_tts, asyncio
    except Exception:
        return None
    try:
        async def _t():
            comm = edge_tts.Communicate(text, "fa-IR-DilaraNeural")
            await comm.save(out_path)
        asyncio.run(_t())
        return out_path if os.path.exists(out_path) else None
    except Exception:
        return None


def prepare(hook_text=None):
    """Return (music_path, voice_path). voice only if TTS available + hook given."""
    music = _find_music()
    voice = None
    if hook_text:
        vp = os.path.join(ROOT, "tmp", "hook_voice.mp3")
        voice = make_voice_hook(hook_text, vp)
    return music, voice


if __name__ == "__main__":
    print("audio_mix loaded. Drop royalty-free music in assets/audio/.")
