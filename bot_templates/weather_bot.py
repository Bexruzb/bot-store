import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

TOKEN = sys.argv[1] if len(sys.argv) > 1 else "TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

CITIES = {
    "toshkent": "Toshkent",
    "samarqand": "Samarqand",
    "buxoro": "Buxoro",
    "fargona": "Farg'ona"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📍 Toshkent", callback_data="city_toshkent")],
        [InlineKeyboardButton("📍 Samarqand", callback_data="city_samarqand")],
        [InlineKeyboardButton("📍 Buxoro", callback_data="city_buxoro")],
        [InlineKeyboardButton("📍 Farg'ona", callback_data="city_fargona")],
        [InlineKeyboardButton("🔍 Boshqa shahar", callback_data="search_city")]
    ]
    
    await update.message.reply_text(
        f"🌤 *OB-HAVO BOTI*\n\n"
        f"Shaharni tanlang yoki nomini yozing:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def show_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, city="Toshkent"):
    query = update.callback_query
    if query:
        await query.answer()
    
    # Demo ob-havo
    weather_data = {
        "Toshkent": {"temp": 25, "humidity": 65, "wind": 12, "desc": "Quyoshli"},
        "Samarqand": {"temp": 22, "humidity": 70, "wind": 8, "desc": "Bulutli"},
        "Buxoro": {"temp": 28, "humidity": 45, "wind": 15, "desc": "Quyoshli"},
        "Farg'ona": {"temp": 20, "humidity": 75, "wind": 10, "desc": "Yomg'ir"}
    }
    
    w = weather_data.get(city, {"temp": 23, "humidity": 60, "wind": 10, "desc": "Ochiq"})
    
    text = f"""
🌤 *{city} ob-havosi*

🌡 Harorat: {w['temp']}°C
💧 Namlik: {w['humidity']}%
🌬 Shamol: {w['wind']} km/soat
☀️ {w['desc']}

🤖 *Bot Store Uz*
    """
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Yangilash", callback_data=f"city_{city.lower()}")],
                [InlineKeyboardButton("◀️ Orqaga", callback_data="start")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "start":
        await start(update, context)
    elif data.startswith("city_"):
        city_eng = data.replace("city_", "")
        city_name = CITIES.get(city_eng, "Toshkent")
        await show_weather(update, context, city_name)
    elif data == "search_city":
        await query.edit_message_text(
            "🔍 Shahar nomini yozing:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Orqaga", callback_data="start")]
            ])
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    await show_weather(update, context, city)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"🌤 Ob-havo boti ishga tushdi! Admin: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
