import asyncio
import os
import httpx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

import db
import twitter
from config import BOT_TOKEN, ADMIN_IDS

CHECK_INTERVAL = 60

def is_admin(update: Update):
    return update.effective_user.id in ADMIN_IDS

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text("Bot ready.\nUse /panel")

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    kb = [
        [InlineKeyboardButton("➕ Add X Username", callback_data="add_user")],
        [InlineKeyboardButton("➖ Remove X Username", callback_data="remove_user")],
        [InlineKeyboardButton("📋 List Usernames", callback_data="list_users")],
        [InlineKeyboardButton("🎯 Set Target Channel", callback_data="set_channel")],
        [InlineKeyboardButton("▶ Start Monitoring", callback_data="start_monitor")],
        [InlineKeyboardButton("⏹ Stop Monitoring", callback_data="stop_monitor")]
    ]

    await update.message.reply_text(
        "🛠 Control Panel",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= BUTTON HANDLER =================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_user":
        context.user_data["await_add"] = True
        await query.edit_message_text("Send X username to ADD (without @)")
        return

    if data == "remove_user":
        context.user_data["await_remove"] = True
        await query.edit_message_text("Send X username to REMOVE")
        return

    if data == "list_users":
        users = await db.get_usernames()
        if not users:
            text = "No usernames added."
        else:
            text = "Monitored accounts:\n\n"
            text += "\n".join([f"• {u[0]}" for u in users])
        await query.edit_message_text(text)
        return

    if data == "set_channel":
        context.user_data["await_channel"] = True
        await query.edit_message_text("Send channel ID (example -1001234567890)")
        return

    if data == "start_monitor":
        await db.set_setting("monitoring", "1")
        await query.edit_message_text("Monitoring started.")
        return

    if data == "stop_monitor":
        await db.set_setting("monitoring", "0")
        await query.edit_message_text("Monitoring stopped.")
        return

# ================= TEXT INPUT =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    text = update.message.text.strip()

    if context.user_data.get("await_add"):
        await db.add_username(text)
        context.user_data["await_add"] = False
        await update.message.reply_text(f"Added: {text}")
        return

    if context.user_data.get("await_remove"):
        await db.remove_username(text)
        context.user_data["await_remove"] = False
        await update.message.reply_text(f"Removed: {text}")
        return

    if context.user_data.get("await_channel"):
        await db.set_setting("target_channel", text)
        context.user_data["await_channel"] = False
        await update.message.reply_text("Channel saved.")
        return

# ================= MONITOR LOOP =================

async def monitor_loop(app):
    await db.init()

    while True:
        monitoring = await db.get_setting("monitoring", "0")
        if monitoring != "1":
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        channel = await db.get_setting("target_channel")
        if not channel:
            await asyncio.sleep(CHECK_INTERVAL)
            continue

        usernames = await db.get_usernames()

        for username, last_id in usernames:
            try:
                user_id = await twitter.get_user_id(username)
                data = await twitter.get_tweets(user_id, last_id)

                tweets = data.get("data", [])
                includes = data.get("includes", {})

                for tweet in reversed(tweets):
                    text = tweet["text"]
                    images, video = twitter.extract_media(tweet, includes)

                    if video:
                        async with httpx.AsyncClient() as client:
                            r = await client.get(video)
                            file_name = f"{tweet['id']}.mp4"
                            with open(file_name, "wb") as f:
                                f.write(r.content)

                        await app.bot.send_video(
                            chat_id=int(channel),
                            video=open(file_name, "rb"),
                            caption=text
                        )
                        os.remove(file_name)

                    elif images:
                        await app.bot.send_photo(
                            chat_id=int(channel),
                            photo=images[0],
                            caption=text
                        )

                    else:
                        await app.bot.send_message(
                            chat_id=int(channel),
                            text=text
                        )

                    await db.update_last_id(username, tweet["id"])

            except Exception as e:
                print(f"Error for {username}: {e}")

        await asyncio.sleep(CHECK_INTERVAL)

# ================= MAIN =================

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    asyncio.create_task(monitor_loop(app))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
