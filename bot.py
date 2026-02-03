import os
import json
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from PIL import Image, ImageEnhance, ImageDraw, ImageFont

# ================== CONFIG ==================
BOT_TOKEN = "8580135563:AAHOqll9NDDJY2MmCL7h3QHIxbCNC5DmDkY"

ADMIN_ID = 6744509694   # <-- apna numeric telegram ID

INSTAGRAM = "https://instagram.com/adarshheartbeat"
YOUTUBE = "https://youtube.com/@adarshheartbeat"
CHANNEL = "https://t.me/adarshheartbeat"

FREE_CREDITS = 8
DATA_FILE = "users.json"

WATERMARK_TEXT = "© Adarsh Heartbeat"
FONT_PATH = "Roboto-Bold.ttf"

# ============================================


# ---------- USER DATA ----------
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)


users = load_users()


from datetime import date

def get_user(uid):
    uid = str(uid)
    today = date.today().isoformat()

    if uid not in users:
        users[uid] = {
            "unlocked": False,
            "credits": FREE_CREDITS,   # first time = 8
            "last_reset": today
        }
        save_users()
        return users[uid]

    user = users[uid]

    # FIX missing keys (old users)
    if "credits" not in user:
        user["credits"] = FREE_CREDITS
    if "unlocked" not in user:
        user["unlocked"] = False
    if "last_reset" not in user:
        user["last_reset"] = today

    # 🔁 DAILY RESET LOGIC
    if user["last_reset"] != today:
        user["credits"] = 5
        user["last_reset"] = today
        save_users()

        # notify user
        try:
            from telegram.helpers import escape_markdown
            return user
        except:
            pass

    save_users()
    return user



# ---------- START ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)

    keyboard = [
        [InlineKeyboardButton("📸 Follow Instagram", url=INSTAGRAM)],
        [InlineKeyboardButton("▶️ Subscribe YouTube", url=YOUTUBE)],
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL)],
        [InlineKeyboardButton("✅ All Done", callback_data="unlock")]
    ]

    await update.message.reply_text(
        "🔒 **Access Locked**\n\n"
        "Use karne se pehle:\n"
        "• Instagram follow\n"
        "• YouTube subscribe\n"
        "• Telegram channel join\n\n"
        "Phir **All Done** dabao.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ---------- UNLOCK ----------
async def unlock(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    user = get_user(uid)
    user["unlocked"] = True
    save_users()

    await query.message.reply_text(
        f"✅ **Unlocked!**\n\n"
        f"Free credits: {user['credits']}\n"
        f"Ab photo bhejo 📷",
        parse_mode="Markdown"
    )


# ---------- PHOTO HANDLER ----------
async def photo_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # ❌ Admin ko auto reply nahi
    if uid == ADMIN_ID:
        return

    user = get_user(uid)

    if not user["unlocked"]:
        await update.message.reply_text("❌ Pehle /start karo aur unlock karo.")
        return

    if user["credits"] <= 0:
        keyboard = [
            [InlineKeyboardButton("💳 Upgrade Plan", callback_data="upgrade")]
        ]
        await update.message.reply_text(
            "🚫 Credits khatam ho gaye.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text("⏳ Photo enhance ho rahi hai...")

    # -------- DOWNLOAD PHOTO --------
    photo = update.message.photo[-1]
    file = await photo.get_file()
    input_path = f"input_{uid}.jpg"
    await file.download_to_drive(input_path)

    # -------- IMAGE PROCESS --------
    img = Image.open(input_path).convert("RGB")
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    img = ImageEnhance.Contrast(img).enhance(1.3)

    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 30)

    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    w, h = img.size
    x = w - tw - 20
    y = h - th - 20

    draw.text((x, y), WATERMARK_TEXT, fill=(255, 255, 255), font=font)

    out_path = f"enhanced_{uid}.jpg"
    img.save(out_path)

    # -------- SEND TO USER --------
    await ctx.bot.send_photo(
        chat_id=uid,
        photo=open(out_path, "rb"),
        caption="✅ Enhanced photo ready"
    )

    # -------- SEND TO ADMIN --------
    await ctx.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=open(out_path, "rb"),
        caption=f"📩 User {uid} | Remaining {user['credits']-1}"
    )

    user["credits"] -= 1
    save_users()

    os.remove(input_path)
    os.remove(out_path)


# ---------- UPGRADE ----------
async def upgrade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("₹10 = 10 Photos", callback_data="pay")],
        [InlineKeyboardButton("₹20 = 25 Photos", callback_data="pay")]
    ]

    await query.message.reply_text(
        "💎 **Upgrade Plans**\n\n"
        "Payment ke baad admin manually credits add karega.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ---------- PAYMENT QR ----------
async def pay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await ctx.bot.send_photo(
        chat_id=query.from_user.id,
        photo=open("payment_qr.jpg", "rb"),
        caption="💳 UPI se pay karo aur screenshot admin ko bhejo."
    )


# ---------- ADMIN ADD CREDITS ----------
async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Usage: /add USER_ID CREDITS"
        )
        return

    try:
        uid = str(int(context.args[0]))
        credits = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid number format")
        return

    user = get_user(uid)
    user["credits"] += credits
    save_users()

    # ✅ ADMIN CONFIRMATION
    await update.message.reply_text(
        f"✅ {credits} credits added to user {uid}"
    )

    # ✅ USER NOTIFICATION (YEH NAYA PART HAI)
    try:
        await context.bot.send_message(
            chat_id=int(uid),
            text=(
                "🎉 **Credits Added!**\n\n"
                f"Admin has added **{credits} credits** to your account.\n"
                f"💳 Total credits now: **{user['credits']}**\n\n"
                "You can now send photos 📸"
            ),
            parse_mode="Markdown"
        )
    except:
        # agar user ne bot block kar diya ho
        pass


async def send_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Reply to the edited photo with:\n/send USER_ID"
        )
        return

    if not update.message.reply_to_message.photo:
        await update.message.reply_text("❌ Please reply to a photo.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /send USER_ID")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid USER_ID")
        return

    photo_id = update.message.reply_to_message.photo[-1].file_id

    await context.bot.send_photo(
        chat_id=target_id,
        photo=photo_id,
        caption="✅ Your edited image is ready."
    )

    await update.message.reply_text("✅ Photo sent to user.")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(unlock, pattern="unlock"))
    app.add_handler(CallbackQueryHandler(upgrade, pattern="upgrade"))
    app.add_handler(CallbackQueryHandler(pay, pattern="pay"))
    app.add_handler(CommandHandler("add", add_credits))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CommandHandler("send", send_back))


    print("✅ Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
