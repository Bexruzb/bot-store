import sys
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

TOKEN = sys.argv[1] if len(sys.argv) > 1 else "YOUR_TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

print(f"Admin bot ishga tushmoqda... Admin ID: {ADMIN_ID}")

BAD_WORDS = ["spam", "reklama", "firibgar", "xxx"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        keyboard = ReplyKeyboardMarkup([
            ["⚙️ Filtr sozlamalari", "👥 A'zolar"],
            ["📊 Statistika", "🚫 Ban/Mute"]
        ], resize_keyboard=True)
        await update.message.reply_text(
            f"👑 *Guruh Boshqaruv Boti*\n\nAdmin panelga xush kelibsiz!",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("Bu bot guruh admini uchun.")

async def filter_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    for word in BAD_WORDS:
        if word in text:
            try:
                await update.message.delete()
                await update.message.reply_text(
                    f"⚠️ {update.message.from_user.first_name}, taqiqlangan so'z!"
                )
            except:
                pass
            return

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"👋 Xush kelibsiz, {member.full_name}!\n"
            f"📋 Qoidalar bilan tanishing!"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_message))
    
    print(f"✅ Admin bot ishga tushdi! Admin: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
