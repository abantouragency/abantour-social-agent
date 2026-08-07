"""
orchestrator_render.py — the single entry point that runs on Render.
It:
  - serves the Flask web API (PC -> Render staging, health)
  - runs the control bot (Telegram + Bale) for admin commands
  - (optional) a scheduler that pings the PC to produce at morning/evening
Render health-check hits /health so the free tier stays warm.
"""
import os, sys, threading
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "modules"))

import state_db
from web_api import app as flask_app


def _start_bot():
    try:
        import control_bot
        control_bot.run()
    except Exception as e:
        state_db.log("ERROR", f"bot start failed: {e}")


def main():
    state_db.init()
    state_db.log("INFO", "orchestrator starting")
    # bot in a background thread (Flask runs in main thread)
    t = threading.Thread(target=_start_bot, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
