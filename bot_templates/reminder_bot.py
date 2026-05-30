import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

TOKEN = sys.argv[1] if len(sys.argv) > 1 else "TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

reminders = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Eslatma qo'shish", callback_data="add_reminder")],
        [InlineKeyboardButton("📋 Eslatmalarim", callback_data="my_reminders")],
        [InlineKeyboardButton("❌ Eslatma o'chirish", callback_data="delete_reminder")]
    ]
    
    await update.message.reply_text(
        f"📝 *ESLATMA BOTI*\n\n"
        f"Salom, {update.effective_user.first_name}!\n"
        f"Men sizga muhim narsalarni eslatib turaman.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def add_reminder_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    context.user_data['adding_reminder'] = True
    
    await query.edit_message_text(
        "📝 Eslatma matnini yozing:\n"
        "Masalan: 'Ertaga soat 9 da uchrashuv'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('adding_reminder'):
        text = update.message.text
        user_id = update.message.from_user.id
        
        if user_id not in reminders:
            reminders[user_id] = []
        
        reminders[user_id].append({
            "text": text,
            "date": datetime.now().isoformat()
        })
        
        context.user_data['adding_reminder'] = False
        
        await update.message.reply_text(
            f"✅ Eslatma saqlandi!\n\n📝 {text}\n\nEslatmalaringizni ko'rish: /start"
        )
    else:
        await update.message.reply_text("Menyudan foydalaning: /start")

async def my_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_reminders = reminders.get(user_id, [])
    
    if not user_reminders:
        text = "📋 Hozircha eslatmalaringiz yo'q!"
    else:
        text = "📋 *ESLATMALARIM*\n\n"
        for i, r in enumerate(user_reminders, 1):
            text += f"{i}. {r['text']}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yangi eslatma", callback_data="add_reminder")],
            [InlineKeyboardButton("◀️ Orqaga", callback_data="start")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_reminder":
        await add_reminder_prompt(update, context)
    elif query.data == "my_reminders":
        await my_reminders(update, context)
    elif query.data == "start":
        await start(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"📝 Eslatma boti ishga tushdi! Admin: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
