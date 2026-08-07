"""
control_bot.py — internal admin bot for the social agent. Runs on Render.
Supports BOTH Telegram and Bale (Bale uses the same Bot API, different base URL).
Commands:
  /start          welcome + help
  /status         growth + queue stats
  /pending        list staged items
  /publish <id>   publish a staged item to its platforms
  /now <pillar>   force-produce one item now (asks Render worker)
  /logs           recent error/info logs
  /help           this menu
Only ADMIN_ID(s) can use it.
"""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "modules"))
from flask import Flask  # ensure flask present; not used here directly
import state_db, telegram_pub

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, ContextTypes
    HAVE_PTB = True
except Exception:
    HAVE_PTB = False

ADMINS = [int(x) for x in os.environ.get("ADMIN_IDS", "67391189").split(",") if x.strip()]
RENDER_BASE = os.environ.get("RENDER_BASE", "")  # e.g. https://social-agent.onrender.com


def _allowed(uid):
    return uid in ADMINS


def _fmt_status():
    s = state_db.stats()
    lines = [
        "📊 *وضعیت ایجنت*",
        f"کل آیتم‌ها: {s['total']}",
        f"آماده انتشار: {s['staged']}",
        f"منتشر شده: {s['published']}",
    ]
    return "\n".join(lines)


def _fmt_pending():
    items = state_db.pending()
    if not items:
        return "✅ چیزی برای انتشار نیست."
    out = ["📥 *محتوای آماده:*"]
    for it in items:
        out.append(f"• `{it['id']}` — {it.get('pillar')}/{it.get('slot')}\n  {it.get('topic')}")
    out.append("\nانتشار: /publish <id>")
    return "\n".join(out)


async def cmd_start(update, ctx):
    if not _allowed(update.effective_user.id):
        return await update.message.reply_text("❌ دسترسی ندارید.")
    await update.message.reply_text(
        "🤖 *ربات کنترل AbanTour Social Agent*\n\n"
        "/status وضعیت\n/pending لیست آماده‌ها\n/publish <id> انتشار\n"
        "/now <pillar> تولید فوری\n/logs لاگ‌ها\n/help راهنما",
        parse_mode="Markdown")


async def cmd_status(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    await update.message.reply_text(_fmt_status(), parse_mode="Markdown")


async def cmd_pending(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    await update.message.reply_text(_fmt_pending(), parse_mode="Markdown")


async def cmd_publish(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    if not ctx.args:
        return await update.message.reply_text("استفاده: /publish <id>")
    item_id = ctx.args[0]
    # fetch item
    item = next((i for i in state_db.pending() if i["id"] == item_id), None)
    if not item:
        return await update.message.reply_text("❌ آیتم پیدا نشد یا قبلاً منتشر شده.")
    await update.message.reply_text("⏳ در حال انتشار...")
    results = []
    # TELEGRAM
    try:
        if item.get("reel_url"):
            telegram_pub.send_video(item["reel_url"], item.get("caption", ""), public=True)
        if item.get("info_url"):
            telegram_pub.send_photo(item["info_url"], item.get("caption", ""), public=True)
        results.append("تلگرام ✅")
    except Exception as e:
        results.append(f"تلگرام ❌ {e}")
    # INSTAGRAM
    try:
        if item.get("reel_url"):
            # instagram_pub expects a public URL
            telegram_pub  # placeholder; real call:
            # instagram_pub.publish_reel(item["reel_url"], item.get("caption",""))
            results.append("اینستا ⏳ (نیاز به توکن)")
    except Exception as e:
        results.append(f"اینستا ❌ {e}")
    state_db.set_published(item_id, ["telegram"])
    await update.message.reply_text("نتیجه:\n" + "\n".join(results))


async def cmd_now(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    pillar = ctx.args[0] if ctx.args else "deals"
    # Ask the Render worker to produce now (via web API if configured)
    if RENDER_BASE:
        import urllib.request
        try:
            req = urllib.request.Request(f"{RENDER_BASE}/api/produce_now",
                data=json.dumps({"pillar": pillar}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=30)
            return await update.message.reply_text(f"🎬 درخواست تولید فوری برای {pillar} ارسال شد.")
        except Exception as e:
            return await update.message.reply_text(f"❌ خطا: {e}")
    await update.message.reply_text("RENDER_BASE تنظیم نشده.")


async def cmd_logs(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    rows = state_db.recent_logs(15)
    if not rows:
        return await update.message.reply_text("لاگی نیست.")
    out = ["📜 *لاگ:*"]
    for r in reversed(rows):
        out.append(f"[{r['level']}] {r['ts']} {r['msg']}")
    await update.message.reply_text("\n".join(out), parse_mode="Markdown")


async def cmd_help(update, ctx):
    return await cmd_start(update, ctx)


def run():
    if not HAVE_PTB:
        print("python-telegram-bot not installed.")
        return
    state_db.init()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    bale_token = os.environ.get("BALE_BOT_TOKEN")
    apps = []
    if tg_token:
        apps.append(Application.builder().token(tg_token).build())
    if bale_token:
        # Bale uses a custom base URL
        apps.append(Application.builder().token(bale_token)
                    .base_url("https://tapi.bale.ai/bot").build())
    for app in apps:
        for h in [CommandHandler("start", cmd_start), CommandHandler("status", cmd_status),
                  CommandHandler("pending", cmd_pending), CommandHandler("publish", cmd_publish),
                  CommandHandler("now", cmd_now), CommandHandler("logs", cmd_logs),
                  CommandHandler("help", cmd_help)]:
            app.add_handler(h)
    if not apps:
        print("No bot tokens configured.")
        return
    import asyncio
    loop = asyncio.get_event_loop()
    for app in apps:
        loop.run_until_complete(app.initialize())
        loop.run_until_complete(app.start())
        loop.run_until_complete(app.updater.start_polling())
    loop.run_forever()


if __name__ == "__main__":
    run()
