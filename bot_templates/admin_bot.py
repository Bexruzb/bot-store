import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime, timedelta

TOKEN = sys.argv[1] if len(sys.argv) > 1 else "TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

# Taqiqlangan so'zlar
BAD_WORDS = ["spam", "reklama", "firibgar"]

# Guruh sozlamalari
group_settings = {
    "welcome_enabled": True,
    "antispam_enabled": True,
    "max_messages": 5,  # 5 ta xabar 10 soniyada
    "ban_duration": 24  # soat
}

user_messages = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("⚙️ Filtr sozlamalari", callback_data="filter_settings")],
            [InlineKeyboardButton("👥 A'zolar ro'yxati", callback_data="members")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
            [InlineKeyboardButton("🔇 Mute/Ban sozlamalari", callback_data="restrictions")]
        ]
        text = "👑 *ADMIN PANEL*\n\nGuruh boshqaruv botiga xush kelibsiz!"
    else:
        text = "📊 Bu bot guruh admini uchun."
        return
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi a'zo qo'shilganda"""
    if not group_settings["welcome_enabled"]:
        return
    
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"👋 Xush kelibsiz, {member.full_name}!\n"
            f"📋 Guruh qoidalarini o'qing!"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlarni tekshirish"""
    if not group_settings["antispam_enabled"]:
        return
    
    user_id = update.message.from_user.id
    text = update.message.text.lower()
    
    # Taqiqlangan so'zlarni tekshirish
    for word in BAD_WORDS:
        if word in text:
            await update.message.delete()
            await update.message.reply_text(
                f"⚠️ {update.message.from_user.first_name}, taqiqlangan so'z ishlatdingiz!"
            )
            return
    
    # Spam tekshirish
    now = datetime.now()
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    user_messages[user_id].append(now)
    
    # 10 soniya ichida 5 tadan ko'p xabar
    recent = [t for t in user_messages[user_id] if (now - t).seconds < 10]
    if len(recent) > group_settings["max_messages"]:
        try:
            await context.bot.restrict_chat_member(
                update.message.chat_id,
                user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=now + timedelta(hours=1)
            )
            await update.message.reply_text(
                f"🚫 {update.message.from_user.first_name} spam uchun 1 soatga cheklandi!"
            )
        except:
            pass

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"📊 Guruh boshqaruvi boti ishga tushdi! Admin: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
