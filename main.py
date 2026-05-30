"""
BOT STORE UZ - Mukammal versiya
Barcha botlar bitta faylda | Tokensiz ishlaydi
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Sozlamalar
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

# Database
conn = sqlite3.connect('botstore.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
    CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, balance INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS subs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_type TEXT, bot_name TEXT, admin_id INTEGER, status TEXT DEFAULT 'active', start_date TEXT, end_date TEXT, price INTEGER);
    CREATE TABLE IF NOT EXISTS bot_tokens (bot_type TEXT PRIMARY KEY, token TEXT, username TEXT);
''')
conn.commit()

# Tayyor bot tokenlari (siz yaratgan botlar)
# Har bir bot uchun @BotFather'dan alohida bot yarating va tokenini qo'ying
BOT_TOKENS = {
    "shop": "SHOP_BOT_TOKEN",
    "admin": "ADMIN_BOT_TOKEN",
    "quiz": "QUIZ_BOT_TOKEN",
    "reminder": "REMINDER_BOT_TOKEN",
    "weather": "WEATHER_BOT_TOKEN"
}

# Botlar katalogi
BOTS = {
    "shop": {"name": "🛍 Mini Do'kon", "icon": "🛍", "price": 10000, "desc": "Mahsulotlar, savatcha, buyurtmalar"},
    "admin": {"name": "📊 Guruh Boshqaruvi", "icon": "📊", "price": 8000, "desc": "Spam filtr, ban, xush kelibsiz"},
    "quiz": {"name": "🎮 Viktorina", "icon": "🎮", "price": 5000, "desc": "Testlar, reyting, mukofotlar"},
    "reminder": {"name": "📝 Eslatma", "icon": "📝", "price": 3000, "desc": "Eslatmalar, takrorlash, ovoz"},
    "weather": {"name": "🌤 Ob-havo", "icon": "🌤", "price": 1000, "desc": "Shaharlar, 7 kunlik, xarita"}
}

# Oddiy menyu
def main_menu(uid=None):
    kb = [
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="balance")],
        [InlineKeyboardButton("🎁 BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ]
    if uid == ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 ADMIN", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def reply_menu():
    return ReplyKeyboardMarkup([
        ["🛍 KATALOG", "📦 BOTLARIM"],
        ["💰 BALANS", "🎁 BONUS"],
        ["📞 ALOQA"]
    ], resize_keyboard=True)

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
              (user.id, user.username, user.full_name))
    conn.commit()
    
    text = f"🤖 *BOT STORE UZ*\n\n👋 Salom, {user.first_name}!\n\n🔥 5 ta bot | 7 kun BEPUL"
    
    await update.message.reply_text(text, reply_markup=reply_menu(), parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text("📋 *Menyu:*", reply_markup=main_menu(user.id), parse_mode=ParseMode.MARKDOWN)

# ============ KATALOG ============
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    text = "🎯 *KATALOG*\n\n7 kun BEPUL sinov!\n\n"
    kb = []
    
    for bid, bot in BOTS.items():
        text += f"{bot['icon']} *{bot['name']}* - {bot['price']:,} so'm\n"
        kb.append([InlineKeyboardButton(
            f"{bot['icon']} {bot['name']} | {bot['price']:,} so'm",
            callback_data=f"info_{bid}"
        )])
    
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")])
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BOT HAQIDA ============
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("info_", "")
    bot = BOTS.get(bid)
    if not bot: return
    
    text = f"*{bot['icon']} {bot['name']}*\n\n📝 {bot['desc']}\n💰 {bot['price']:,} so'm/kun\n🆓 7 kun BEPUL"
    
    kb = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL OLISH", callback_data=f"get_{bid}")],
        [InlineKeyboardButton("💳 SOTIB OLISH", callback_data=f"buy_{bid}")],
        [InlineKeyboardButton("◀️ KATALOG", callback_data="catalog")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BOTNI OLISH ============
async def get_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("get_", "")
    bot = BOTS.get(bid)
    if not bot: return
    
    user = update.effective_user
    
    # Tekshirish: oldin olganmi?
    c.execute("SELECT * FROM subs WHERE user_id = ? AND bot_type = ? AND status = 'active'",
              (user.id, bid))
    if c.fetchone():
        await query.edit_message_text(
            "❌ Siz bu botni allaqachon olgansiz!\n📦 /mybots",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 BOTLARIM", callback_data="my_bots")]])
        )
        return
    
    # Token mavjudligini tekshirish
    token = BOT_TOKENS.get(bid)
    if not token or token == f"{bid.upper()}_BOT_TOKEN":
        await query.edit_message_text(
            f"⚠️ Bu bot hozircha mavjud emas.\n\n"
            f"Admin yangi bot yaratmoqda.\n"
            f"Tez orada qo'shiladi!\n\n"
            f"📞 {ADMIN_USERNAME}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ KATALOG", callback_data="catalog")]])
        )
        return
    
    # Admin ID so'rash
    context.user_data['getting_bot'] = bid
    context.user_data['step'] = 'waiting_admin_id'
    
    await query.edit_message_text(
        f"🔑 *{bot['name']}*\n\n"
        f"Bot sizga biriktiriladi!\n\n"
        f"📝 Admin ID'ngizni kiriting:\n"
        f"(@userinfobot dan oling)\n\n"
        f"❌ /cancel - bekor qilish",
        parse_mode=ParseMode.MARKDOWN
    )

# ============ ADMIN ID QABUL QILISH ============
async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ID raqam bo'lishi kerak! @userinfobot dan oling.")
        return
    
    bid = context.user_data.get('getting_bot')
    bot = BOTS.get(bid)
    if not bot: return
    
    user = update.effective_user
    
    # Bazaga saqlash
    now = datetime.now()
    end = now + timedelta(days=7)
    
    c.execute(
        "INSERT INTO subs (user_id, bot_type, bot_name, admin_id, start_date, end_date, price) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user.id, bid, bot['name'], admin_id, now.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), bot['price'])
    )
    conn.commit()
    
    # Tozalash
    for k in ['getting_bot', 'step']:
        if k in context.user_data:
            del context.user_data[k]
    
    token = BOT_TOKENS.get(bid, "Tez orada")
    
    await update.message.reply_text(
        f"✅ *BOT OLINDI!*\n\n"
        f"🤖 {bot['name']}\n"
        f"👑 Admin ID: `{admin_id}`\n"
        f"📅 Bepul: {end.strftime('%d.%m.%Y')} gacha\n"
        f"💰 Keyin: {bot['price']:,} so'm/kun\n\n"
        f"🔗 Bot: @{token.replace('_BOT_TOKEN', '') if 'BOT_TOKEN' not in token else 'tez_orada'}\n\n"
        f"⚠️ Bot 24 soat ichida to'liq ishga tushiriladi!\n"
        f"📞 {ADMIN_USERNAME}",
        reply_markup=reply_menu(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Admin'ga xabar
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 Yangi bot olindi!\n👤 {user.full_name}\n"
            f"🤖 {bot['name']}\n👑 Admin: {admin_id}\n"
            f"📅 {end.strftime('%d.%m.%Y')} gacha",
            parse_mode=ParseMode.MARKDOWN
        )
    except: pass

# ============ MENING BOTLARIM ============
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    user_id = update.effective_user.id
    c.execute("SELECT * FROM subs WHERE user_id = ? AND status = 'active' ORDER BY id DESC", (user_id,))
    subs = c.fetchall()
    
    if not subs:
        text = "📦 Hali botlaringiz yo'q!"
        kb = [[InlineKeyboardButton("🛍 KATALOG", callback_data="catalog")]]
    else:
        text = "📦 *MENING BOTLARIM*\n\n"
        kb = []
        for s in subs:
            try:
                end = datetime.strptime(s[7], '%Y-%m-%d')
                days = (end - datetime.now()).days
            except:
                days = 0
            text += f"✅ {s[3]}\n👑 `{s[4]}`\n⏳ {max(0, days)} kun\n\n"
        kb.append([InlineKeyboardButton("🛍 YANGI BOT", callback_data="catalog")])
    
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")])
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BUY ============
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("buy_", "")
    bot = BOTS.get(bid)
    if not bot: return
    
    text = f"💳 *{bot['name']}*\n\n💰 {bot['price']:,} so'm/kun\n\nTo'lov:\n📱 Click: +998901234567\n💳 Payme: 8600xxxx1234\n\nChekni shu yerga yuboring!"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ ORQAGA", callback_data=f"info_{bid}")]
    ]), parse_mode=ParseMode.MARKDOWN)

# ============ BALANS ============
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    c.execute("SELECT balance FROM users WHERE user_id = ?", (update.effective_user.id,))
    user = c.fetchone()
    bal = user[0] if user else 0
    
    text = f"💰 Balans: {bal} so'm"
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]
        ]))
    else:
        await update.message.reply_text(text, reply_markup=reply_menu())

# ============ BONUS ============
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (update.effective_user.id,))
    conn.commit()
    
    text = "🎁 100 so'm bonus qo'shildi!"
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]
        ]))
    else:
        await update.message.reply_text(text, reply_markup=reply_menu())

# ============ CONTACT ============
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    text = f"📞 Admin: {ADMIN_USERNAME}\n\nSavollar bo'lsa yozing!"
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]
        ]))
    else:
        await update.message.reply_text(text, reply_markup=reply_menu())

# ============ ADMIN ============
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    if update.effective_user.id != ADMIN_ID: return
    
    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subs WHERE status = 'active'")
    bots = c.fetchone()[0]
    
    text = f"👑 *ADMIN*\n\n👥 Foydalanuvchilar: {users}\n🤖 Aktiv botlar: {bots}"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]
    ]), parse_mode=ParseMode.MARKDOWN)

# ============ CALLBACK ROUTER ============
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    try: await query.answer()
    except: pass
    
    try:
        if data == "start": await start(update, context)
        elif data == "catalog": await catalog(update, context)
        elif data == "my_bots": await my_bots(update, context)
        elif data == "balance": await balance(update, context)
        elif data == "bonus": await bonus(update, context)
        elif data == "contact": await contact(update, context)
        elif data == "admin": await admin(update, context)
        elif data.startswith("info_"): await bot_info(update, context)
        elif data.startswith("get_"): await get_bot(update, context)
        elif data.startswith("buy_"): await buy(update, context)
    except Exception as e:
        logger.error(f"Callback xatosi: {e}")
        try:
            await query.edit_message_text("⚠️ /start yozing")
        except: pass

# ============ TEXT ROUTER ============
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Admin ID kiritish
    if context.user_data.get('step') == 'waiting_admin_id':
        await process_admin_id(update, context)
        return
    
    # Menyu
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
        for k in ['getting_bot', 'step']:
            if k in context.user_data:
                del context.user_data[k]
        await update.message.reply_text("❌ Bekor qilindi!", reply_markup=reply_menu())
    else:
        await update.message.reply_text("Menyudan foydalaning!", reply_markup=reply_menu())

# ============ PHOTO ============
async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Chek qabul qilindi! Admin tez orada tasdiqlaydi.")
    try:
        await context.bot.forward_message(ADMIN_ID, update.message.from_user.id, update.message.message_id)
    except: pass

# ============ MAIN ============
def main():
    logger.info("="*40)
    logger.info("🚀 BOT STORE UZ - SODDA VERSIYA")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info("="*40)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("mybots", my_bots))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    
    logger.info("🔥 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
