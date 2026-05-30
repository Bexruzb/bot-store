# BOT STORE UZ - Tuzatilgan versiya
import os
import sqlite3
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
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        full_name TEXT, 
        balance INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        bot_type TEXT, 
        bot_token TEXT, 
        bot_username TEXT, 
        status TEXT DEFAULT 'active', 
        start_date TEXT, 
        end_date TEXT
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        amount INTEGER, 
        date TEXT
    );
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
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)", 
            (user.id, user.username, user.full_name)
        )
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
    
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
    bot = BOTS.get(bot_id)
    
    if not bot:
        await query.edit_message_text("Bot topilmadi!")
        return
    
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
    
    # Oldin olinganmi tekshirish
    cursor.execute(
        "SELECT * FROM subscriptions WHERE user_id = ? AND bot_type = ? AND status = 'active'", 
        (user_id, bot_id)
    )
    if cursor.fetchone():
        await query.edit_message_text("❌ Siz bu botni allaqachon olgansiz!\n📦 Mening botlarim: /start")
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
    bot = BOTS.get(bot_id, {"name": "Noma'lum"})
    
    try:
        from telegram import Bot
        temp = Bot(token=token)
        info = await temp.get_me()
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        cursor.execute(
            "INSERT INTO subscriptions (user_id, bot_type, bot_token, bot_username, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, bot_id, token, info.username, start_date.isoformat(), end_date.isoformat())
        )
        conn.commit()
        
        del context.user_data['activating']
        
        # Admin'ga xabar
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 Yangi faollashtirish!\n👤 ID: `{user_id}`\n🤖 {bot['name']}\n🔑 Token: `{token}`\n📅 Tugash: {end_date.strftime('%d.%m.%Y')}",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Admin xabari yuborilmadi: {e}")
        
        await update.message.reply_text(
            f"✅ *TABRIKLAYMIZ!*\n\n🤖 Bot: @{info.username}\n📅 Bepul: {end_date.strftime('%d.%m.%Y')} gacha\n⏰ 24/7 ishlaydi!\n\nSavollar: /start",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"Token error: {error_msg}")
        
        if "Unauthorized" in error_msg:
            await update.message.reply_text("❌ Token noto'g'ri! @BotFather'dan yangi token oling.")
        elif "Conflict" in error_msg:
            await update.message.reply_text("❌ Bu token boshqa botda ishlatilgan. Yangi bot yarating.")
        else:
            await update.message.reply_text(f"❌ Xatolik! Token noto'g'ri.\n\nIltimos @BotFather'dan yangi token oling va qayta yuboring.")

# Mening botlarim
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    cursor.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,))
    subs = cursor.fetchall()
    
    if not subs:
        await query.edit_message_text(
            "📦 Hali botlaringiz yo'q!\n\n🛍 Katalogni ko'rish uchun:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛍 Katalogga o'tish", callback_data="catalog")]])
        )
        return
    
    text = "📦 *MENING BOTLARIM*\n\n"
    keyboard = []
    
    for sub in subs:
        bot = BOTS.get(sub[2])
        if bot:
            try:
                end_date = datetime.fromisoformat(sub[6])
                days = (end_date - datetime.now()).days
                text += f"✅ {bot['name']}\n⏳ Qolgan: {max(0, days)} kun\n🤖 @{sub[5]}\n\n"
            except:
                text += f"✅ {bot['name']}\n🤖 @{sub[5]}\n\n"
    
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
        f"💰 Balans: {balance_amount} so'm\n\n💳 To'ldirish uchun:\n📱 Click: +998901234567\n💳 Payme: 8600xxxx1234\n\nChekni shu yerga yuboring!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ORQAGA", callback_data="main_menu")]])
    )

# Rasm qabul qilish (chek)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    await update.message.reply_text("✅ Chek qabul qilindi!\n⏰ Admin tez orada tasdiqlaydi.")
    
    # Admin'ga forward
    try:
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )
        await context.bot.send_message(
            ADMIN_ID,
            f"💳 Yangi to'lov cheki!\n👤 User ID: `{user_id}`",
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Chek forward error: {e}")

# Yordam
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📞 *YORDAM*\n\n"
        "1️⃣ Katalogdan bot tanlang\n"
        "2️⃣ @BotFather'dan token oling\n"
        "3️⃣ Tokenni yuboring\n"
        "4️⃣ Bot 7 kun BEPUL ishlaydi!\n\n"
        "💰 Keyin kuniga 300 so'm\n"
        "📞 Admin: @yoldoshev_3",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ORQAGA", callback_data="main_menu")]])
    )

# Admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ Ruxsat yo'q!")
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'")
    active = cursor.fetchone()[0]
    
    text = f"👨‍💼 *ADMIN PANEL*\n\n👥 Foydalanuvchilar: {users}\n🤖 Aktiv botlar: {active}"
    
    await query.edit_message_text(
        text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ ORQAGA", callback_data="main_menu")]])
    )

# Asosiy funksiya
def main():
    print("🚀 Bot ishga tushmoqda...")
    
    # Application yaratish
    app = Application.builder().token(TOKEN).build()
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    
    # Callback handlerlar
    app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(bot_info, pattern="^info_"))
    app.add_handler(CallbackQueryHandler(activate_bot, pattern="^activate_"))
    app.add_handler(CallbackQueryHandler(my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(help_cmd, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(admin, pattern="^admin$"))
    
    # Message handlerlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token))
    
    print("✅ Bot Store Uz ishga tushdi!")
    print("📱 Telegram'da /start yozing!")
    
    # Polling boshlash
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
