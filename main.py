"""
BOT STORE UZ - FAQAT DO'KON
Botlarni qo'lda ishga tushirasiz
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

# Database
conn = sqlite3.connect('botstore.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
    CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, balance INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_name TEXT, admin_id INTEGER, status TEXT DEFAULT 'new', date TEXT, price INTEGER);
''')
conn.commit()

# Botlar
BOTS = {
    "shop": {"name": "🛍 Mini Do'kon", "price": 10000, "desc": "Mahsulotlar katalogi, savatcha, buyurtmalar"},
    "admin": {"name": "📊 Guruh Boshqaruvi", "price": 8000, "desc": "Spam filtr, ban, xush kelibsiz xabari"},
    "quiz": {"name": "🎮 Viktorina", "price": 5000, "desc": "Testlar yaratish, reyting tizimi"},
    "reminder": {"name": "📝 Eslatma", "price": 3000, "desc": "Eslatmalar, takrorlash, ovozli eslatma"},
    "weather": {"name": "🌤 Ob-havo", "price": 1000, "desc": "Shaharlar ob-havosi, 7 kunlik prognoz"}
}

# Menyu
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 BUYURTMA BERISH", callback_data="order")],
        [InlineKeyboardButton("📋 BUYURTMALARIM", callback_data="my_orders")],
        [InlineKeyboardButton("💰 BALANS", callback_data="balance")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ])

def reply_kb():
    return ReplyKeyboardMarkup([
        ["🛍 KATALOG", "📦 BUYURTMA"],
        ["📋 BUYURTMALARIM", "💰 BALANS"],
        ["📞 ALOQA"]
    ], resize_keyboard=True)

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
              (user.id, user.username, user.full_name))
    conn.commit()
    
    text = f"""
🤖 *BOT STORE UZ*

👋 Salom, {user.first_name}!

🔥 *5 ta professional Telegram bot*
✅ *7 kun BEPUL sinov*
💰 *1 000 - 10 000 so'm/kun*

⚡️ Botlar qo'lda ishga tushiriladi
📞 Admin 24/7 yordam beradi

Tugmalardan foydalaning:
    """
    
    await update.message.reply_text(text, reply_markup=reply_kb(), parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text("📋 *Menyu:*", reply_markup=main_menu_kb(), parse_mode=ParseMode.MARKDOWN)

# ============ KATALOG ============
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n"
    kb = []
    
    for bid, bot in BOTS.items():
        text += f"{bot['name']} - {bot['price']:,} so'm/kun\n"
        text += f"└ {bot['desc']}\n\n"
        kb.append([InlineKeyboardButton(
            f"{bot['name']} | {bot['price']:,} so'm",
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
    
    text = f"""
*{bot['name']}*

📝 {bot['desc']}
💰 Narx: {bot['price']:,} so'm/kun
🆓 7 kun BEPUL sinov

⚡️ Nima qilmoqchisiz?
    """
    
    kb = [
        [InlineKeyboardButton("📦 BUYURTMA BERISH", callback_data=f"order_{bid}")],
        [InlineKeyboardButton("◀️ KATALOG", callback_data="catalog")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BUYURTMA BERISH ============
async def order_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        data = query.data
        if data.startswith("order_"):
            bid = data.replace("order_", "")
            context.user_data['ordering'] = bid
    
    if context.user_data.get('ordering'):
        bot = BOTS.get(context.user_data['ordering'])
        if bot:
            await query.edit_message_text(
                f"📝 *{bot['name']}* buyurtmasi\n\n"
                f"Admin ID'ngizni kiriting:\n"
                f"(@userinfobot dan oling)\n\n"
                f"❌ /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['step'] = 'waiting_id'
    else:
        text = "📦 *BUYURTMA BERISH*\n\nQaysi botni xohlaysiz?"
        kb = []
        for bid, bot in BOTS.items():
            kb.append([InlineKeyboardButton(f"{bot['name']} | {bot['price']:,} so'm", callback_data=f"order_{bid}")])
        kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")])
        
        if query:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ ADMIN ID QABUL ============
async def process_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ID raqam bo'lishi kerak!")
        return
    
    bid = context.user_data.get('ordering')
    bot = BOTS.get(bid)
    if not bot: return
    
    user = update.effective_user
    
    # Buyurtmani saqlash
    c.execute(
        "INSERT INTO orders (user_id, bot_name, admin_id, date, price) VALUES (?, ?, ?, ?, ?)",
        (user.id, bot['name'], admin_id, datetime.now().strftime('%Y-%m-%d'), bot['price'])
    )
    conn.commit()
    
    for k in ['ordering', 'step']:
        if k in context.user_data:
            del context.user_data[k]
    
    await update.message.reply_text(
        f"✅ *BUYURTMA QABUL QILINDI!*\n\n"
        f"🤖 {bot['name']}\n"
        f"👑 Admin ID: `{admin_id}`\n"
        f"📅 7 kun BEPUL\n"
        f"💰 Keyin: {bot['price']:,} so'm/kun\n\n"
        f"⏰ Admin 24 soat ichida bog'lanadi va botni ishga tushiradi!\n"
        f"📞 {ADMIN_USERNAME}",
        reply_markup=reply_kb(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Admin'ga xabar
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 *YANGI BUYURTMA!*\n\n"
            f"👤 {user.full_name} (@{user.username})\n"
            f"🆔 {user.id}\n"
            f"🤖 {bot['name']}\n"
            f"👑 Admin ID: `{admin_id}`\n"
            f"💰 {bot['price']:,} so'm\n\n"
            f"Botni ishga tushirish kerak!",
            parse_mode=ParseMode.MARKDOWN
        )
    except: pass

# ============ BUYURTMALARIM ============
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    c.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (update.effective_user.id,))
    orders = c.fetchall()
    
    if not orders:
        text = "📋 Hali buyurtmalaringiz yo'q!"
    else:
        text = "📋 *BUYURTMALARIM*\n\n"
        for o in orders:
            status_emoji = {"new": "🆕", "done": "✅", "cancel": "❌"}
            text += f"{status_emoji.get(o[4], '📋')} {o[2]}\n"
            text += f"👑 Admin: `{o[3]}`\n"
            text += f"📅 {o[5]}\n\n"
    
    kb = [[InlineKeyboardButton("📦 YANGI BUYURTMA", callback_data="order")],
          [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BALANS ============
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    c.execute("SELECT balance FROM users WHERE user_id = ?", (update.effective_user.id,))
    user = c.fetchone()
    bal = user[0] if user else 0
    
    text = f"💰 Balans: {bal} so'm\n\n💳 To'ldirish: {ADMIN_USERNAME}"
    kb = [[InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, reply_markup=reply_kb())

# ============ CONTACT ============
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    
    text = f"📞 Admin: {ADMIN_USERNAME}"
    kb = [[InlineKeyboardButton("🏠 BOSH MENYU", callback_data="start")]]
    
    if query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, reply_markup=reply_kb())

# ============ CALLBACK ROUTER ============
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    try: await query.answer()
    except: pass
    
    routes = {
        "start": start, "catalog": catalog, "order": order_bot,
        "my_orders": my_orders, "balance": balance, "contact": contact
    }
    
    if data in routes:
        await routes[data](update, context)
    elif data.startswith("info_"):
        await bot_info(update, context)
    elif data.startswith("order_"):
        await order_bot(update, context)

# ============ TEXT ROUTER ============
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if context.user_data.get('step') == 'waiting_id':
        await process_id(update, context)
    elif text == "🛍 KATALOG": await catalog(update, context)
    elif text == "📦 BUYURTMA": await order_bot(update, context)
    elif text == "📋 BUYURTMALARIM": await my_orders(update, context)
    elif text == "💰 BALANS": await balance(update, context)
    elif text == "📞 ALOQA": await contact(update, context)
    elif text == "/cancel":
        for k in ['ordering', 'step']:
            if k in context.user_data: del context.user_data[k]
        await update.message.reply_text("❌ Bekor qilindi!", reply_markup=reply_kb())
    else:
        await update.message.reply_text("Menyudan foydalaning!", reply_markup=reply_kb())

# ============ MAIN ============
def main():
    logger.info("🚀 BOT STORE UZ - Do'kon boti")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    
    logger.info("🔥 Ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
