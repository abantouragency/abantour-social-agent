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
import os, sys, json, threading, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "modules"))
from flask import Flask  # ensure flask present; not used here directly
import state_db, telegram_pub

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
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
    items = state_db.pending()
    if not items:
        return await update.message.reply_text("✅ چیزی برای انتشار نیست.")
    # inline keyboard: one row per item with a Publish button
    kb = []
    for it in items[:10]:
        label = f"انتشار: {it.get('pillar')}/{it.get('slot')}"
        kb.append([InlineKeyboardButton(label, callback_data=f"pub:{it['id']}")])
    kb.append([InlineKeyboardButton("🔄 رفرش", callback_data="refresh_pending")])
    await update.message.reply_text(
        "📥 *محتوای آماده — روی دکمه بزنید:*",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_publish(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    if not ctx.args:
        return await update.message.reply_text("استفاده: /publish <id>")
    item_id = ctx.args[0]
    item = next((i for i in state_db.pending() if i["id"] == item_id), None)
    if not item:
        return await update.message.reply_text("❌ آیتم پیدا نشد یا قبلاً منتشر شده.")
    await _do_publish(update, item_id, item)


async def _do_publish(update, item_id, item, edit=False):
    await update.message.reply_text("⏳ در حال انتشار...")
    results = []
    chan = os.environ.get("TELEGRAM_CHANNEL_PUBLIC", "")
    try:
        if item.get("reel_url"):
            r = telegram_pub.publish_public(chan, item["reel_url"], item.get("caption", ""), kind="video")
            results.append(f"تلگرام ریلز {'✅' if r.get('ok') else '❌ ' + str(r.get('error', ''))[:60]}")
        if item.get("info_url"):
            r = telegram_pub.publish_public(chan, item["info_url"], item.get("caption", ""), kind="photo")
            results.append(f"تلگرام اینفو {'✅' if r.get('ok') else '❌ ' + str(r.get('error', ''))[:60]}")
    except Exception as e:
        results.append(f"تلگرام ❌ {e}")
    if item.get("reel_url"):
        results.append("اینستا ⏳ (توکن تنظیم نشده)")
    state_db.set_published(item_id, ["telegram"])
    msg = "نتیجه:\n" + "\n".join(results)
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)


async def btn_callback(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    q = update.callback_query
    await q.answer()
    data = q.data
    if data == "refresh_pending":
        items = state_db.pending()
        if not items:
            return await q.edit_message_text("✅ چیزی برای انتشار نیست.")
        kb = []
        for it in items[:10]:
            kb.append([InlineKeyboardButton(f"انتشار: {it.get('pillar')}/{it.get('slot')}", callback_data=f"pub:{it['id']}")])
        kb.append([InlineKeyboardButton("🔄 رفرش", callback_data="refresh_pending")])
        return await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    if data.startswith("pub:"):
        item_id = data[4:]
        item = next((i for i in state_db.pending() if i["id"] == item_id), None)
        if not item:
            return await q.edit_message_text("❌ قبلاً منتشر شده یا حذف شد.")
        # reuse publish logic (reply via callback query message)
        await _do_publish(update, item_id, item, edit=True)


async def cmd_now(update, ctx):
    if not _allowed(update.effective_user.id):
        return
    pillar = ctx.args[0] if ctx.args else "deals"
    # write request into state_db; PC watchdog pulls it via /api/pc_requests
    try:
        state_db.add_pc_request(pillar)
        return await update.message.reply_text(
            f"🎬 درخواست تولید فوری برای ستون «{pillar}» ثبت شد.\n"
            f"PC شما (در صورت روشن بودن + اجرای watchdog) آن را می‌سازد و به صف اضافه می‌کند.")
    except Exception as e:
        return await update.message.reply_text(f"❌ خطا: {e}")


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

    def _start_app(app, label):
        import asyncio
        try:
            asyncio.run(_run_polling(app, label))
        except Exception as e:
            state_db.log("ERROR", f"{label} bot crashed: {e}")

    async def _run_polling(app, label):
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        state_db.log("INFO", f"{label} bot started")
        state_db.set_flag(f"bot_{label}_alive", "1")
        # keep alive until stopped
        import asyncio as aio
        try:
            while True:
                await aio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            state_db.set_flag(f"bot_{label}_alive", "0")
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    threads = []
    if tg_token:
        tg_app = Application.builder().token(tg_token).build()
        _register(tg_app)
        t = threading.Thread(target=_start_app, args=(tg_app, "Telegram"), daemon=True)
        t.start(); threads.append(t)
    if bale_token:
        bale_app = Application.builder().token(bale_token).base_url("https://tapi.bale.ai/bot").build()
        _register(bale_app)
        t = threading.Thread(target=_start_app, args=(bale_app, "Bale"), daemon=True)
        t.start(); threads.append(t)
    if not threads:
        print("No bot tokens configured.")
        return
    # NOTE: this is called from a daemon thread inside the orchestrator,
    # so we must NOT join() here (that would block Flask in the main thread).
    # The daemon threads keep polling until the process exits.


def _register(app):
    for h in [CommandHandler("start", cmd_start), CommandHandler("status", cmd_status),
              CommandHandler("pending", cmd_pending), CommandHandler("publish", cmd_publish),
              CommandHandler("now", cmd_now), CommandHandler("logs", cmd_logs),
              CommandHandler("help", cmd_help),
              CallbackQueryHandler(btn_callback)]:
        app.add_handler(h)


if __name__ == "__main__":
    run()
