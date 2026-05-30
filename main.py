"""
🤖 BOT STORE UZ - Full Xatosiz Versiya
Token + Admin ID so'rash | Bot ishga tushirish | Monitoring
"""

import sqlite3
import logging
import os
import sys
import subprocess
import asyncio
import signal
import threading
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, Bot
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# ============ SOZLAMALAR ============
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

# ============ DATABASE ============
class DB:
    def __init__(self):
        self.conn = sqlite3.connect('botstore.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self._init()
    
    def _init(self):
        self.c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
                balance INTEGER DEFAULT 0, bonus_date TEXT
            );
            CREATE TABLE IF NOT EXISTS subs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                bot_type TEXT, bot_token TEXT UNIQUE, bot_username TEXT,
                bot_name TEXT, admin_id INTEGER, status TEXT DEFAULT 'trial',
                is_running INTEGER DEFAULT 0, start_date TEXT, end_date TEXT,
                price INTEGER DEFAULT 0, pid INTEGER DEFAULT 0
            );
        ''')
        self.conn.commit()
    
    def execute(self, q, p=()):
        self.c.execute(q, p)
        self.conn.commit()
    
    def fetchone(self, q, p=()):
        self.c.execute(q, p)
        return self.c.fetchone()
    
    def fetchall(self, q, p=()):
        self.c.execute(q, p)
        return self.c.fetchall()

db = DB()

# ============ BOTLAR ============
BOTS = {
    "shop": {"name": "🛍 Mini Do'kon", "icon": "🛍", "file": "shop_bot.py", "price": 10000, "cat": "Biznes"},
    "admin": {"name": "📊 Guruh Boshqaruv", "icon": "📊", "file": "admin_bot.py", "price": 8000, "cat": "Hamjamiyat"},
    "quiz": {"name": "🎮 Viktorina", "icon": "🎮", "file": "quiz_bot.py", "price": 5000, "cat": "Ta'lim"},
    "reminder": {"name": "📝 Eslatma", "icon": "📝", "file": "reminder_bot.py", "price": 3000, "cat": "Produktivlik"},
    "weather": {"name": "🌤 Ob-havo", "icon": "🌤", "file": "weather_bot.py", "price": 1000, "cat": "Ma'lumot"}
}

# ============ KEYBOARDLAR ============
def main_reply():
    return ReplyKeyboardMarkup([
        ["🛍 KATALOG", "📦 BOTLARIM"],
        ["💰 BALANS", "🎁 BONUS"],
        ["💳 TO'LOV", "📞 YORDAM"]
    ], resize_keyboard=True)

def main_inline(uid=None):
    kb = [
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="payment")],
        [InlineKeyboardButton("🎁 KUNLIK BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ]
    if uid == ADMIN_ID:
        kb.append([InlineKeyboardButton("👑 ADMIN", callback_data="admin")])
    return InlineKeyboardMarkup(kb)

def back_btn(data="main_menu"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ ORQAGA", callback_data=data)],
        [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
    ])

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
               (user.id, user.username, user.full_name))
    
    text = f"🤖 *BOT STORE UZ*\n\n👋 Salom, {user.first_name}!\n\n🔥 5 ta bot | 7 kun BEPUL"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=main_inline(user.id), parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(text, reply_markup=main_reply(), parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text("📋 *Menyu:*", reply_markup=main_inline(user.id), parse_mode=ParseMode.MARKDOWN)

# ============ KATALOG ============
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *KATALOG*\n\n"
    kb = []
    for bid, bot in BOTS.items():
        text += f"{bot['icon']} {bot['name']} - {bot['price']:,} so'm\n"
        kb.append([InlineKeyboardButton(f"{bot['icon']} {bot['name']} | {bot['price']:,} so'm", callback_data=f"info_{bid}")])
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BOT HAQIDA ============
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("info_", "")
    bot = BOTS.get(bid)
    if not bot:
        return
    
    text = f"*{bot['icon']} {bot['name']}*\n\n💰 {bot['price']:,} so'm/kun\n🆓 7 kun BEPUL"
    kb = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL SINASH", callback_data=f"activate_{bid}")],
        [InlineKeyboardButton("💳 SOTIB OLISH", callback_data=f"buy_{bid}")],
        [InlineKeyboardButton("◀️ KATALOG", callback_data="catalog")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ FAOLSHTIRISH ============
async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("activate_", "")
    bot = BOTS.get(bid)
    if not bot:
        return
    
    context.user_data['activating'] = bid
    context.user_data['step'] = 'token'
    
    text = f"🔑 *{bot['name']}*\n\n1️⃣ @BotFather'ga o'ting\n2️⃣ /newbot yozing\n3️⃣ TOKENni yuboring\n\n❌ /cancel"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="cancel_act")]
    ]), parse_mode=ParseMode.MARKDOWN)

# ============ TOKEN QABUL ============
async def process_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    
    if ':' not in token or len(token) < 45:
        await update.message.reply_text("❌ Noto'g'ri token! @BotFather'dan /newbot qiling.")
        return
    
    if db.fetchone("SELECT * FROM subs WHERE bot_token = ?", (token,)):
        await update.message.reply_text("❌ Bu token band! Yangi bot yarating.")
        return
    
    msg = await update.message.reply_text("⏳ Tekshirilmoqda...")
    
    try:
        test = Bot(token=token)
        info = await test.get_me()
        
        context.user_data['token'] = token
        context.user_data['bot_username'] = info.username
        context.user_data['step'] = 'admin_id'
        
        await msg.delete()
        await update.message.reply_text(
            f"✅ Token OK!\n🤖 @{info.username}\n\n"
            f"2️⃣ Admin ID kiriting:\n@userinfobot dan ID oling.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await msg.delete()
        await update.message.reply_text(f"❌ Token xato!\n\n{str(e)[:100]}")

# ============ ADMIN ID QABUL ============
async def process_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admin_id = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ID raqam bo'lishi kerak!")
        return
    
    msg = await update.message.reply_text("⏳ Bot ishga tushirilmoqda...")
    
    bid = context.user_data['activating']
    token = context.user_data['token']
    username = context.user_data['bot_username']
    bot = BOTS.get(bid)
    
    # Bazaga saqlash
    now = datetime.now()
    end = now + timedelta(days=7)
    db.execute(
        "INSERT INTO subs (user_id, bot_type, bot_token, bot_username, bot_name, admin_id, start_date, end_date, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (update.message.from_user.id, bid, token, username, bot['name'], admin_id,
         now.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'), bot['price'])
    )
    
    # Botni ishga tushirish
    result = run_bot(token, bot['file'], admin_id)
    
    await msg.delete()
    
    # Tozalash
    for k in ['activating', 'token', 'bot_username', 'step']:
        if k in context.user_data:
            del context.user_data[k]
    
    if result:
        await update.message.reply_text(
            f"✅ *BOT ISHGA TUSHIRILDI!*\n\n"
            f"🤖 @{username}\n📦 {bot['name']}\n👑 Admin: `{admin_id}`\n"
            f"📅 Bepul: {end.strftime('%d.%m.%Y')} gacha\n\n"
            f"Botingiz: @{username}",
            reply_markup=main_reply(), parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚠️ Bot saqlandi lekin ishga tushmadi.\n\n"
            f"Sababi: bot fayli topilmadi yoki xatolik.\n"
            f"Admin tez orada tuzatadi.\n\n"
            f"📞 {ADMIN_USERNAME}",
            reply_markup=main_reply()
        )

# ============ BOTNI ISHGA TUSHIRISH ============
def run_bot(token, bot_file, admin_id):
    """Botni ishga tushirish - SODDA va ISHONCHLI"""
    bot_path = f"bot_templates/{bot_file}"
    
    logger.info(f"Bot ishga tushirilmoqda: {bot_path}")
    
    # Fayl mavjudligini tekshirish
    if not os.path.exists(bot_path):
        logger.error(f"❌ Fayl topilmadi: {bot_path}")
        # Papkadagi fayllarni ko'rsatish
        if os.path.exists("bot_templates"):
            files = os.listdir("bot_templates")
            logger.info(f"Papkadagi fayllar: {files}")
        return False
    
    try:
        # Oddiy ishga tushirish
        cmd = [sys.executable, bot_path, token, str(admin_id)]
        logger.info(f"Buyruq: {' '.join(cmd)}")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 2 soniya kutish va tekshirish
        import time
        time.sleep(2)
        
        if process.poll() is None:
            logger.info(f"✅ Bot ishga tushdi! PID={process.pid}")
            return True
        else:
            stdout, stderr = process.communicate()
            logger.error(f"❌ Bot o'ldi!")
            logger.error(f"STDOUT: {stdout.decode() if stdout else 'None'}")
            logger.error(f"STDERR: {stderr.decode() if stderr else 'None'}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Xatolik: {e}")
        return False

# ============ MENING BOTLARIM ============
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subs = db.fetchall("SELECT * FROM subs WHERE user_id = ? AND status IN ('trial', 'active') ORDER BY id DESC",
                       (update.effective_user.id,))
    
    if not subs:
        text = "📦 Hali botlaringiz yo'q!"
        kb = [[InlineKeyboardButton("🛍 KATALOG", callback_data="catalog")]]
    else:
        text = "📦 *MENING BOTLARIM*\n\n"
        kb = []
        for s in subs:
            try:
                end = datetime.strptime(s[11], '%Y-%m-%d %H:%M:%S')
                days = (end - datetime.now()).days
            except:
                days = 0
            text += f"{'✅' if s[9] else '⚠️'} {s[5]}\n🤖 @{s[4]}\n👑 `{s[6]}`\n⏳ {max(0, days)} kun\n\n"
            kb.append([InlineKeyboardButton(f"⚙️ {s[5][:20]}", callback_data=f"manage_{s[0]}")])
        kb.append([InlineKeyboardButton("🛍 YANGI BOT", callback_data="catalog")])
    
    kb.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ BOT BOSHQARUVI ============
async def manage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    sid = int(query.data.replace("manage_", ""))
    s = db.fetchone("SELECT * FROM subs WHERE id = ?", (sid,))
    if not s:
        return
    
    try:
        end = datetime.strptime(s[11], '%Y-%m-%d %H:%M:%S')
        days = (end - datetime.now()).days
    except:
        days = 0
    
    text = f"⚙️ *{s[5]}*\n\n🤖 @{s[4]}\n👑 `{s[6]}`\n⏳ {max(0, days)} kun\n🔄 {'✅ Ishlayapti' if s[9] else '⚠️ Toxtagan'}"
    kb = [
        [InlineKeyboardButton("🔄 QAYTA ISHGA TUSHIRISH", callback_data=f"restart_{sid}")],
        [InlineKeyboardButton("⏹ TO'XTATISH", callback_data=f"stop_{sid}")],
        [InlineKeyboardButton("◀️ ORQAGA", callback_data="my_bots")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ RESTART BOT ============
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    sid = int(query.data.replace("restart_", ""))
    s = db.fetchone("SELECT * FROM subs WHERE id = ?", (sid,))
    if not s:
        return
    
    bot = BOTS.get(s[2])
    if bot:
        result = run_bot(s[3], bot['file'], s[6])
        if result:
            db.execute("UPDATE subs SET is_running = 1, pid = 0 WHERE id = ?", (sid,))
            await query.edit_message_text("✅ Qayta ishga tushirildi!", reply_markup=back_btn("my_bots"))
        else:
            await query.edit_message_text("❌ Ishga tushirib bo'lmadi!", reply_markup=back_btn("my_bots"))

# ============ STOP BOT ============
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    sid = int(query.data.replace("stop_", ""))
    db.execute("UPDATE subs SET status = 'stopped', is_running = 0 WHERE id = ?", (sid,))
    await query.edit_message_text("⏹ To'xtatildi", reply_markup=back_btn("my_bots"))

# ============ BUY BOT ============
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bid = query.data.replace("buy_", "")
    bot = BOTS.get(bid)
    if not bot:
        return
    
    text = f"💳 *{bot['name']}*\n\n💰 {bot['price']:,} so'm/kun\n\nTo'lov:\n📱 Click: +998901234567\n💳 Payme: 8600xxxx1234\n\nChekni yuboring!"
    await query.edit_message_text(text, reply_markup=back_btn(f"info_{bid}"), parse_mode=ParseMode.MARKDOWN)

# ============ BONUS ============
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    today = datetime.now().strftime('%Y-%m-%d')
    user = db.fetchone("SELECT * FROM users WHERE user_id = ?", (update.effective_user.id,))
    
    if user and str(user[4]) != today:
        db.execute("UPDATE users SET balance = balance + 100, bonus_date = ? WHERE user_id = ?",
                   (today, update.effective_user.id))
        text = "🎁 100 so'm bonus qo'shildi!"
    else:
        text = "⏰ Bugun olgansiz!"
    
    await query.edit_message_text(text, reply_markup=back_btn())

# ============ PAYMENT / BALANS ============
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.fetchone("SELECT * FROM users WHERE user_id = ?", (update.effective_user.id,))
    bal = user[3] if user else 0
    
    text = f"💰 Balans: {bal} so'm\n\n💳 To'lov:\n📱 Click: +998901234567\n💳 Payme: 8600xxxx1234\n\nChekni yuboring!"
    await query.edit_message_text(text, reply_markup=back_btn())

# ============ CONTACT ============
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"📞 {ADMIN_USERNAME}", reply_markup=back_btn())

# ============ ADMIN ============
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    users = db.fetchone("SELECT COUNT(*) FROM users")[0]
    bots = db.fetchone("SELECT COUNT(*) FROM subs WHERE status IN ('trial', 'active')")[0]
    
    text = f"👑 *ADMIN*\n\n👥 {users}\n🤖 {bots}"
    kb = [[InlineKeyboardButton("🔄 HAMMASINI QAYTA ISHGA TUSHIRISH", callback_data="restart_all")],
          [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# ============ RESTART ALL ============
async def restart_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    subs = db.fetchall("SELECT * FROM subs WHERE status IN ('trial', 'active')")
    count = 0
    for s in subs:
        bot = BOTS.get(s[2])
        if bot:
            if run_bot(s[3], bot['file'], s[6]):
                db.execute("UPDATE subs SET is_running = 1 WHERE id = ?", (s[0],))
                count += 1
    
    await query.edit_message_text(f"✅ {count} ta bot qayta ishga tushirildi!", reply_markup=back_btn("admin"))

# ============ CANCEL ============
async def cancel_act(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    for k in ['activating', 'token', 'bot_username', 'step']:
        if k in context.user_data:
            del context.user_data[k]
    await query.edit_message_text("❌ Bekor qilindi", reply_markup=back_btn("catalog"))

# ============ CALLBACK ROUTER ============
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha callback'lar"""
    query = update.callback_query
    data = query.data
    
    try:
        await query.answer()
    except:
        pass
    
    try:
        if data == "main_menu": await start(update, context)
        elif data == "catalog": await catalog(update, context)
        elif data == "my_bots": await my_bots(update, context)
        elif data == "bonus": await bonus(update, context)
        elif data == "payment": await payment(update, context)
        elif data == "contact": await contact(update, context)
        elif data == "admin": await admin(update, context)
        elif data == "restart_all": await restart_all(update, context)
        elif data == "cancel_act": await cancel_act(update, context)
        elif data.startswith("info_"): await bot_info(update, context)
        elif data.startswith("activate_"): await activate(update, context)
        elif data.startswith("buy_"): await buy(update, context)
        elif data.startswith("manage_"): await manage(update, context)
        elif data.startswith("restart_"): await restart(update, context)
        elif data.startswith("stop_"): await stop(update, context)
        else:
            logger.warning(f"Noma'lum callback: {data}")
    except Exception as e:
        logger.error(f"Callback xatosi [{data}]: {e}")
        try:
            await query.edit_message_text("⚠️ Xatolik! /start yozing.")
        except:
            pass

# ============ TEXT ROUTER ============
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha matnli xabarlar"""
    text = update.message.text
    user = update.effective_user
    step = context.user_data.get('step')
    
    # Token/ID kiritish
    if step == 'token':
        await process_token(update, context)
        return
    elif step == 'admin_id':
        await process_admin_id(update, context)
        return
    
    # Menyu
    if text == "🛍 KATALOG":
        await catalog(update, context)
    elif text == "📦 BOTLARIM":
        await my_bots(update, context)
    elif text == "💰 BALANS":
        u = db.fetchone("SELECT balance FROM users WHERE user_id = ?", (user.id,))
        await update.message.reply_text(f"💰 {u[3] if u else 0} so'm", reply_markup=main_reply())
    elif text == "🎁 BONUS":
        await bonus(update, context)
    elif text == "💳 TO'LOV":
        await payment(update, context)
    elif text == "📞 YORDAM":
        await contact(update, context)
    elif text == "/cancel":
        for k in ['activating', 'token', 'bot_username', 'step']:
            if k in context.user_data:
                del context.user_data[k]
        await update.message.reply_text("❌ Bekor qilindi!", reply_markup=main_reply())
    else:
        await update.message.reply_text("Menyudan foydalaning!", reply_markup=main_inline(user.id))

# ============ PHOTO ROUTER ============
async def photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Chek qabul qilindi!")
    try:
        await context.bot.forward_message(ADMIN_ID, update.message.from_user.id, update.message.message_id)
    except:
        pass

# ============ ERROR ============
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xatolik: {context.error}")

# ============ MAIN ============
def main():
    logger.info("="*40)
    logger.info("🚀 BOT STORE UZ")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info("="*40)
    
    # Papka
    os.makedirs("bot_templates", exist_ok=True)
    
    # Fayllarni tekshirish
    for bid, bot in BOTS.items():
        path = f"bot_templates/{bot['file']}"
        if os.path.exists(path):
            logger.info(f"✅ {bot['file']} - mavjud")
        else:
            logger.error(f"❌ {bot['file']} - YO'Q!")
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.PHOTO, photo_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    app.add_error_handler(error_handler)
    
    logger.info("🔥 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
