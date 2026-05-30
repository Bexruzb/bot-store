import sys
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

TOKEN = sys.argv[1] if len(sys.argv) > 1 else "TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

# Testlar
quizzes = {}
scores = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("➕ Test qo'shish", callback_data="add_quiz")],
            [InlineKeyboardButton("📋 Testlar ro'yxati", callback_data="quiz_list")],
            [InlineKeyboardButton("📊 Natijalar", callback_data="results")],
            [InlineKeyboardButton("🎮 Test o'ynash", callback_data="play")]
        ]
        text = "👑 *VIKTORINA ADMIN*\n\nTestlar yarating va o'ynang!"
    else:
        keyboard = [[InlineKeyboardButton("🎮 Test o'ynash", callback_data="play")]]
        text = "🎮 *VIKTORINA*\n\nBilimingizni sinab ko'ring!"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def play_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demo test"""
    question = "O'zbekiston poytaxti?"
    options = ["Toshkent", "Samarqand", "Buxoro", "Farg'ona"]
    correct = 0  # Toshkent
    
    keyboard = []
    for i, opt in enumerate(options):
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"answer_{i}_0")])
    
    await update.callback_query.edit_message_text(
        f"🎮 *SAVOL:* {question}\n\nJavobni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, answer, correct = query.data.split("_")
    answer = int(answer)
    correct = int(correct)
    
    if answer == correct:
        await query.edit_message_text("✅ TO'G'RI! Tabriklaymiz! 🎉")
    else:
        await query.edit_message_text("❌ Noto'g'ri! Qayta urinib ko'ring!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "play":
        await play_quiz(update, context)
    else:
        await start(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(play|add_quiz|quiz_list|results)$"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))
    
    print(f"🎮 Viktorina boti ishga tushdi! Admin: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
