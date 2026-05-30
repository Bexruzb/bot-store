import sqlite3, logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930

conn = sqlite3.connect('botstore.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
    CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, balance INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_type TEXT, bot_name TEXT,
        bot_token TEXT, bot_username TEXT, admin_id INTEGER, status TEXT DEFAULT 'active',
        start_date TEXT, end_date TEXT, price INTEGER
    );
''')
conn.commit()

BOTS = {
    "shop": {"name": "🛍 Mini Do'kon Boti", "price": 10000, "desc": "Mahsulotlar, savatcha, buyurtmalar, admin panel"},
    "admin": {"name": "📊 Guruh Boshqaruv Boti", "price": 8000, "desc": "Spam filtr, avto-ban, xush kelibsiz xabari"},
    "quiz": {"name": "🎮 Viktorina Boti", "price": 5000, "desc": "Test yaratish, reyting tizimi, mukofotlar"},
    "reminder": {"name": "📝 Eslatma Boti", "price": 3000, "desc": "Eslatmalar, takrorlash, ovozli eslatma"},
    "weather": {"name": "🌤 Ob-havo Boti", "price": 1000, "desc": "Shaharlar ob-havosi, 7 kunlik prognoz"}
}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="balance")],
        [InlineKeyboardButton("🎁 BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ])

def reply_menu():
    return ReplyKeyboardMarkup([
        ["🛍 KATALOG", "📦 BOTLARIM"],
        ["💰 BALANS", "🎁 BONUS"],
        ["📞 ALOQA"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
              (user.id, user.username, user.full_name))
    conn.commit()
    
    for k in ['step', 'bot_type', 'bot_name']:
        if k in context.user_data: del context.user_data[k]
    
    text = f"🤖 *BOT STORE UZ*\n\n👋 Salom, {user.first_name}!\n\n🔥 5 ta bot | 7 kun BEPUL\n💰 1 000 - 10 000 so'm"
    await update.message.reply_text(text, reply_markup=reply_menu(), parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text("📋 *Menyu:*", reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n7 kun BEPUL sinov!\n\n"
    kb = []
    for bid, bot in BOTS.items():
        text += f"{bot['name']}\n└ {bot['price']:,} so'm/kun\n\n"
        kb.append([InlineKeyboardButton(f"{bot['name']} | {bot['price']:,} so'm", callback_data=f"info_{bid}")])
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("info_", "")
    bot = BOTS.get(bid)
    if not bot: return
    
    text = f"*{bot['name']}*\n\n📝 {bot['desc']}\n💰 {bot['price']:,} so'm/kun\n🆓 7 kun BEPUL"
    kb = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL OLISH", callback_data=f"get_{bid}")],
        [InlineKeyboardButton("💳 SOTIB OLISH", callback_data=f"buy_{bid}")],
        [InlineKeyboardButton("◀️ KATALOG", callback_data="catalog")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

async def get_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("get_", "")
    bot = BOTS.get(bid)
    if not bot: return
    
    c.execute("SELECT * FROM orders WHERE user_id=? AND bot_type=? AND status='active'",
              (update.effective_user.id, bid))
    if c.fetchone():
        await query.edit_message_text("❌ Siz bu botni allaqachon olgansiz!\n📦 /mybots")
        return
    
    context.user_data['bot_type'] = bid
    context.user_data['bot_name'] = bot['name']
    context.user_data['step'] = 'waiting_token'
    
    text = f"🔑 *{bot['name']}*\n\n1️⃣ @BotFather ga o'ting\n2️⃣ /newbot yozing\n3️⃣ Bot yarating\n4️⃣ TOKENni shu yerga yuboring\n\n❌ /cancel"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def process_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    
    if ':' not in token or len(token) < 45:
        await update.message.reply_text("❌ Noto'g'ri token! @BotFather dan /newbot qiling.")
        return
    
    c.execute("SELECT * FROM orders WHERE bot_token=?", (token,))
    if c.fetchone():
        await update.message.reply_text("❌ Bu token band! Yangi bot yarating.")
        return
    
    msg = await update.message.reply_text("⏳ Token tekshirilmoqda...")
    
    try:
        test = Bot(token=token)
        info = await test.get_me()
        
        context.user_data['token'] = token
        context.user_data['bot_username'] = info.username
        context.user_data['step'] = 'waiting_admin_id'
        
        await msg.delete()
        await update.message.reply_text(
            f"✅ Token OK!\n🤖 @{info.username}\n\n"
            f"2️⃣ Admin ID kiriting:\n@userinfobot dan oling",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await msg.delete()
        await update.message.reply_text(f"❌ Token xato! {str(e)[:100]}")

async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ID raqam bo'lishi kerak!")
        return
    
    user = update.effective_user
    bot_type = context.user_data['bot_type']
    bot_name = context.user_data['bot_name']
    token = context.user_data['token']
    bot_username = context.user_data['bot_username']
    
    now = datetime.now()
    end = now + timedelta(days=7)
    
    c.execute(
        "INSERT INTO orders (user_id, bot_type, bot_name, bot_token, bot_username, admin_id, start_date, end_date, price) VALUES (?,?,?,?,?,?,?,?,?)",
        (user.id, bot_type, bot_name, token, bot_username, admin_id,
         now.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), BOTS[bot_type]['price'])
    )
    conn.commit()
    
    for k in ['step', 'bot_type', 'bot_name', 'token', 'bot_username']:
        if k in context.user_data: del context.user_data[k]
    
    await update.message.reply_text(
        f"✅ *BOT RO'YXATGA OLINDI!*\n\n"
        f"🤖 @{bot_username}\n📦 {bot_name}\n👑 Admin: `{admin_id}`\n"
        f"📅 Bepul: {end.strftime('%d.%m.%Y')} gacha\n💰 Keyin: {BOTS[bot_type]['price']:,} so'm\n\n"
        f"⏰ Admin botingizni 24 soat ichida ishga tushiradi!\n📞 @yoldoshev_3",
        reply_markup=reply_menu(), parse_mode=ParseMode.MARKDOWN
    )
    
    await context.bot.send_message(
        ADMIN_ID,
        f"🆕 *YANGI BUYURTMA!*\n\n"
        f"👤 {user.full_name} (@{user.username})\n"
        f"🤖 {bot_name}\n🔑 `{token}`\n"
        f"🔗 @{bot_username}\n👑 Admin ID: `{admin_id}`\n\n"
        f"⚡️ Botni ishga tushirish kerak!",
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Yangi buyurtma: {user.id} - {bot_name}")

async def buy_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bid = query.data.replace("buy_", "")
    bot = BOTS.get(bid)
    await query.edit_message_text(
        f"💳 *{bot['name']}*\n\n💰 {bot['price']:,} so'm\n\n📱 Click: +998901234567\n💳 Payme: 8600xxxx1234\n\nChekni yuboring!",
        parse_mode=ParseMode.MARKDOWN
    )

async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    c.execute("SELECT * FROM orders WHERE user_id=? AND status='active' ORDER BY id DESC",
              (update.effective_user.id,))
    orders = c.fetchall()
    
    if not orders:
        await query.edit_message_text("📦 Hali botlaringiz yo'q!", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 KATALOG", callback_data="catalog")]
        ]))
        return
    
    text = "📦 *MENING BOTLARIM*\n\n"
    for o in orders:
        try:
            end = datetime.strptime(o[8], '%Y-%m-%d')
            days = (end - datetime.now()).days
        except: days = 0
        text += f"✅ {o[3]}\n🤖 @{o[5]}\n👑 `{o[6]}`\n⏳ {max(0,days)} kun\n\n"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 YANGI BOT", callback_data="catalog"), InlineKeyboardButton("🏠 MENYU", callback_data="start")]
    ]), parse_mode=ParseMode.MARKDOWN)

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    c.execute("SELECT balance FROM users WHERE user_id=?", (update.effective_user.id,))
    bal = c.fetchone()
    text = f"💰 Balans: {bal[0] if bal else 0} so'm"
    if query: await query.edit_message_text(text)
    else: await update.message.reply_text(text)

async def bonus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    c.execute("UPDATE users SET balance=balance+100 WHERE user_id=?", (update.effective_user.id,))
    conn.commit()
    if query: await query.edit_message_text("🎁 100 so'm qo'shildi!")
    else: await update.message.reply_text("🎁 100 so'm qo'shildi!")

async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    if query: await query.edit_message_text("📞 @yoldoshev_3")
    else: await update.message.reply_text("📞 @yoldoshev_3")

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    try: await q.answer()
    except: pass
    if d == "start": await start(update, context)
    elif d == "catalog": await catalog(update, context)
    elif d == "my_bots": await my_bots(update, context)
    elif d == "balance": await balance_cmd(update, context)
    elif d == "bonus": await bonus_cmd(update, context)
    elif d == "contact": await contact_cmd(update, context)
    elif d.startswith("info_"): await bot_info(update, context)
    elif d.startswith("get_"): await get_bot(update, context)
    elif d.startswith("buy_"): await buy_bot(update, context)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    step = context.user_data.get('step')
    if step == 'waiting_token': await process_token(update, context)
    elif step == 'waiting_admin_id': await process_admin_id(update, context)
    elif text == "🛍 KATALOG": await catalog(update, context)
    elif text == "📦 BOTLARIM": await my_bots(update, context)
    elif text == "💰 BALANS": await balance_cmd(update, context)
    elif text == "🎁 BONUS": await bonus_cmd(update, context)
    elif text == "📞 ALOQA": await contact_cmd(update, context)
    elif text == "/cancel":
        for k in ['step','bot_type','bot_name','token','bot_username']:
            if k in context.user_data: del context.user_data[k]
        await update.message.reply_text("❌ Bekor qilindi!", reply_markup=reply_menu())
    else: await update.message.reply_text("Menyudan foydalaning!", reply_markup=reply_menu())

def main():
    logger.info("🚀 DO'KON BOTI ISHGA TUSHDI!")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
