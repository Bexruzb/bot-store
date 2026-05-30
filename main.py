"""
🤖 BOT STORE UZ - Professional Do'kon Boti
Admin ID so'rash, botlarni ishga tushirish, monitoring
Barcha xatoliklar tuzatilgan versiya
"""

import sqlite3
import logging
import os
import subprocess
import sys
import asyncio
import signal
import time
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, Bot
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden

# ============ LOGGING ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ KONFIGURATSIYA ============
TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

# ============ BOT JARAYONLARI ============
running_bots = {}  # {sub_id: process}

# ============ DATABASE ============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('botstore.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        self.c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                bonus_date TEXT,
                joined_date TEXT DEFAULT (datetime('now', 'localtime')),
                total_bots INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_type TEXT NOT NULL,
                bot_token TEXT NOT NULL UNIQUE,
                bot_username TEXT,
                bot_name TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                admin_name TEXT,
                status TEXT DEFAULT 'trial',
                is_running INTEGER DEFAULT 0,
                start_date TEXT DEFAULT (datetime('now', 'localtime')),
                end_date TEXT,
                price INTEGER DEFAULT 0,
                pid INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                sub_id INTEGER,
                status TEXT DEFAULT 'pending',
                method TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            
            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sub_id INTEGER,
                event TEXT,
                details TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        ''')
        self.conn.commit()
    
    def execute(self, query, params=()):
        self.c.execute(query, params)
        self.conn.commit()
    
    def fetchone(self, query, params=()):
        self.c.execute(query, params)
        return self.c.fetchone()
    
    def fetchall(self, query, params=()):
        self.c.execute(query, params)
        return self.c.fetchall()
    
    def add_user(self, user_id, username, full_name):
        self.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
    
    def get_user(self, user_id):
        return self.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
    
    def add_balance(self, user_id, amount):
        self.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    
    def claim_bonus(self, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        user = self.get_user(user_id)
        if user:
            bonus_date = str(user[4]) if user[4] else ""
            if bonus_date != today:
                self.execute(
                    "UPDATE users SET balance = balance + 100, bonus_date = ? WHERE user_id = ?",
                    (today, user_id)
                )
                return True, 100
        return False, 0
    
    def add_subscription(self, user_id, bot_type, bot_token, bot_username, bot_name, admin_id):
        start = datetime.now()
        end = start + timedelta(days=7)
        self.execute('''
            INSERT INTO subscriptions 
            (user_id, bot_type, bot_token, bot_username, bot_name, admin_id, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, bot_type, bot_token, bot_username, bot_name, admin_id, 
              start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')))
        sub_id = self.c.lastrowid
        
        self.execute("UPDATE users SET total_bots = total_bots + 1 WHERE user_id = ?", (user_id,))
        return sub_id
    
    def check_token_exists(self, token):
        return self.fetchone("SELECT * FROM subscriptions WHERE bot_token = ?", (token,))
    
    def get_subscription(self, sub_id):
        return self.fetchone("SELECT * FROM subscriptions WHERE id = ?", (sub_id,))
    
    def get_user_subscriptions(self, user_id):
        return self.fetchall(
            "SELECT * FROM subscriptions WHERE user_id = ? AND status IN ('trial', 'active') ORDER BY id DESC",
            (user_id,)
        )
    
    def get_all_active_subscriptions(self):
        return self.fetchall("SELECT * FROM subscriptions WHERE status IN ('trial', 'active')")
    
    def update_subscription_status(self, sub_id, status):
        self.execute("UPDATE subscriptions SET status = ? WHERE id = ?", (status, sub_id))
    
    def update_bot_running(self, sub_id, is_running, pid=0):
        self.execute("UPDATE subscriptions SET is_running = ?, pid = ? WHERE id = ?", 
                    (is_running, pid, sub_id))
    
    def add_log(self, sub_id, event, details=""):
        self.execute("INSERT INTO bot_logs (sub_id, event, details) VALUES (?, ?, ?)",
                    (sub_id, event, details))
    
    def get_stats(self):
        stats = {}
        stats['users'] = self.fetchone("SELECT COUNT(*) FROM users")[0]
        stats['active_bots'] = self.fetchone(
            "SELECT COUNT(*) FROM subscriptions WHERE status IN ('trial', 'active')"
        )[0]
        stats['total_bots'] = self.fetchone("SELECT COUNT(*) FROM subscriptions")[0]
        stats['today_income'] = self.fetchone(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE date(created_at) = date('now', 'localtime')"
        )[0]
        return stats

db = Database()

# ============ 5 TA BOTLAR KATALOGI ============
BOTS = {
    "shop": {
        "id": "shop",
        "name": "🛍 Mini Do'kon Boti",
        "icon": "🛍",
        "desc": """📦 *To'liq do'kon tizimi*
• Mahsulotlar katalogi
• Savatcha va buyurtmalar
• Admin panel
• Statistika va mijozlar bazasi""",
        "file": "shop_bot.py",
        "price": 10000,
        "category": "💼 Biznes"
    },
    "admin": {
        "id": "admin",
        "name": "📊 Guruh Boshqaruv Boti",
        "icon": "📊",
        "desc": """🛡 *Guruh admini uchun*
• Spam va reklama filtr
• Avtomatik ban/mute
• Xush kelibsiz xabari
• Statistika""",
        "file": "admin_bot.py",
        "price": 8000,
        "category": "👥 Hamjamiyat"
    },
    "quiz": {
        "id": "quiz",
        "name": "🎮 Viktorina Boti",
        "icon": "🎮",
        "desc": """🎯 *Test va viktorinalar*
• Test yaratish
• Reyting tizimi
• Mukofotlar
• Natijalar statistikasi""",
        "file": "quiz_bot.py",
        "price": 5000,
        "category": "📚 Ta'lim"
    },
    "reminder": {
        "id": "reminder",
        "name": "📝 Eslatma Boti",
        "icon": "📝",
        "desc": """⏰ *Shaxsiy eslatmalar*
• Vazifa eslatmalari
• Takroriy eslatmalar
• Ovozli eslatmalar
• Kalendar integratsiyasi""",
        "file": "reminder_bot.py",
        "price": 3000,
        "category": "📋 Produktivlik"
    },
    "weather": {
        "id": "weather",
        "name": "🌤 Ob-havo Boti",
        "icon": "🌤",
        "desc": """🌍 *Ob-havo ma'lumotlari*
• Barcha shaharlar
• 7 kunlik prognoz
• Soatlik yangilanish
• Ob-havo xaritasi""",
        "file": "weather_bot.py",
        "price": 1000,
        "category": "🌍 Ma'lumot"
    }
}

# ============ KEYBOARDLAR ============
def get_main_reply_keyboard():
    """Asosiy Reply Keyboard"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛍 KATALOG"), KeyboardButton("📦 BOTLARIM")],
        [KeyboardButton("💰 BALANS"), KeyboardButton("🎁 BONUS")],
        [KeyboardButton("💳 TO'LOV"), KeyboardButton("📞 YORDAM")]
    ], resize_keyboard=True)

def get_main_inline_keyboard(user_id=None):
    """Asosiy Inline Keyboard"""
    keyboard = [
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS TO'LDIRISH", callback_data="payment")],
        [InlineKeyboardButton("🎁 KUNLIK BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_back_button(callback_data="main_menu"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ ORQAGA", callback_data=callback_data)]
    ])

# ============ ASOSIY HANDLERLAR ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi - asosiy menyu"""
    user = update.effective_user
    
    # Foydalanuvchini ro'yxatdan o'tkazish
    db.add_user(user.id, user.username, user.full_name)
    
    welcome_text = f"""
🤖 *BOT STORE UZ* - Professional Bot Do'koni

👋 Salom, *{user.first_name}*!

🔥 *5 ta professional bot*
✅ *7 kun BEPUL sinov*
💰 *1 000 - 10 000 so'm/kun*
🛡 *24/7 ishlash kafolati*

⚡️ Menyudan foydalaning yoki tugmalarni bosing:
    """
    
    # Reply keyboard yuborish
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_reply_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Inline menyu ham yuborish
    await update.message.reply_text(
        "📋 *Menyu:*",
        reply_markup=get_main_inline_keyboard(user.id),
        parse_mode=ParseMode.MARKDOWN
    )

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botlar katalogi"""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n"
    text += "🔥 Barcha botlar 7 kun BEPUL sinov!\n\n"
    
    keyboard = []
    for bot_id, bot in BOTS.items():
        text += f"{bot['icon']} *{bot['name']}*\n"
        text += f"├ 💰 {bot['price']:,} so'm/kun\n"
        text += f"└ 📂 {bot['category']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{bot['icon']} {bot['name']} | {bot['price']:,} so'm",
                callback_data=f"bot_info_{bot_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")])
    
    if query:
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot haqida batafsil ma'lumot"""
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("bot_info_", "")
    bot = BOTS.get(bot_id)
    
    if not bot:
        await query.edit_message_text("❌ Bot topilmadi!", reply_markup=get_back_button())
        return
    
    text = f"""
*{bot['icon']} {bot['name']}*

{bot['desc']}

💰 *Narx:* {bot['price']:,} so'm/kun
🆓 *Bepul sinov:* 7 kun
📂 *Kategoriya:* {bot['category']}

⚡️ *Nima qilmoqchisiz?*
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL SINASH", callback_data=f"activate_{bot_id}")],
        [InlineKeyboardButton("💳 SOTIB OLISH", callback_data=f"buy_{bot_id}")],
        [InlineKeyboardButton("◀️ KATALOGGA QAYTISH", callback_data="catalog")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def activate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni faollashtirish jarayoni - 1-qadam: Token so'rash"""
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("activate_", "")
    bot = BOTS.get(bot_id)
    
    if not bot:
        await query.edit_message_text("❌ Bot topilmadi!")
        return
    
    # Foydalanuvchi holatini saqlash
    context.user_data['activating'] = bot_id
    context.user_data['step'] = 'waiting_token'
    
    text = f"""
🔑 *{bot['name']}* - FAOLSHTIRISH

*1-QADAM: Bot yarating va Token oling*

📱 @BotFather'ga o'ting:
1️⃣ /newbot buyrug'ini yuboring
2️⃣ Bot uchun nom kiriting
3️⃣ Bot uchun username kiriting (oxiri `bot` bilan)
4️⃣ Olingan *TOKEN* ni shu yerga yuboring

⚠️ *Muhim:* Har bir bot uchun alohida token kerak!
❌ Bekor qilish: /cancel

📝 Token namunasi:
`1234567890:AAHdqTcvCHrTabcdefghijklmnopqrs`
    """
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="catalog")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Token qabul qilish - 2-qadam"""
    if 'activating' not in context.user_data:
        return
    
    step = context.user_data.get('step', 'waiting_token')
    
    if step == 'waiting_token':
        token = update.message.text.strip()
        
        # Token formatini tekshirish
        if ':' not in token or len(token) < 45:
            await update.message.reply_text(
                "❌ *Noto'g'ri token formati!*\n\n"
                "Token `1234567890:ABCdef...` ko'rinishida bo'lishi kerak.\n"
                "@BotFather'dan /newbot orqali yangi token oling.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Token mavjudligini tekshirish
        if db.check_token_exists(token):
            await update.message.reply_text(
                "❌ *Bu token allaqachon ishlatilgan!*\n\n"
                "@BotFather'dan YANGI bot yarating va yangi token oling.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Tokenni tekshirish
        processing_msg = await update.message.reply_text("⏳ Token tekshirilmoqda...")
        
        try:
            test_bot = Bot(token=token)
            bot_info = await test_bot.get_me()
            
            # Token to'g'ri, keyingi qadamga o'tish
            context.user_data['token'] = token
            context.user_data['bot_username'] = bot_info.username
            context.user_data['step'] = 'waiting_admin_id'
            
            await processing_msg.delete()
            
            await update.message.reply_text(
                f"✅ *Token qabul qilindi!*\n\n"
                f"🤖 Bot: @{bot_info.username}\n\n"
                f"*2-QADAM: Admin ID'ni kiriting*\n\n"
                f"📱 @userinfobot ga /start yozing\n"
                f"🆔 ID raqamingizni oling\n"
                f"📤 Shu yerga yuboring\n\n"
                f"💡 Masalan: `{ADMIN_ID}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("ℹ️ ID QANDAY OLINADI?", url="https://t.me/userinfobot")],
                    [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="cancel_activate")]
                ])
            )
            
        except Exception as e:
            await processing_msg.delete()
            error_msg = str(e)
            
            if "Unauthorized" in error_msg:
                await update.message.reply_text(
                    "❌ *Token noto'g'ri!*\n\n"
                    "Bu token yaroqsiz. Iltimos @BotFather'dan yangi bot yarating.",
                    parse_mode=ParseMode.MARKDOWN
                )
            elif "Conflict" in error_msg:
                await update.message.reply_text(
                    "❌ *Token band qilingan!*\n\n"
                    "Bu token boshqa botda ishlatilgan. Yangi bot yarating.",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"❌ *Xatolik:* {error_msg[:200]}\n\n"
                    "Iltimos qayta urinib ko'ring.",
                    parse_mode=ParseMode.MARKDOWN
                )
    
    elif step == 'waiting_admin_id':
        await receive_admin_id(update, context)

async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ID qabul qilish va botni ishga tushirish"""
    user = update.effective_user
    
    try:
        admin_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ *Noto'g'ri ID!*\n\n"
            "ID faqat raqamlardan iborat bo'lishi kerak.\n"
            "@userinfobot dan ID'ngizni oling.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # ID ni tekshirish
    if admin_id <= 0:
        await update.message.reply_text("❌ Noto'g'ri ID! Iltimos to'g'ri ID kiriting.")
        return
    
    processing_msg = await update.message.reply_text("⏳ ID tekshirilmoqda va bot ishga tushirilmoqda...")
    
    bot_id = context.user_data['activating']
    token = context.user_data['token']
    bot_username = context.user_data['bot_username']
    bot = BOTS.get(bot_id)
    
    try:
        # Admin ID ga xabar yubora olishini tekshirish
        try:
            await context.bot.send_chat_action(chat_id=admin_id, action="typing")
        except Forbidden:
            await processing_msg.delete()
            await update.message.reply_text(
                "⚠️ *Ogohlantirish:* Bot bu ID ga xabar yubora olmaydi.\n"
                "Lekin bot baribir ishga tushiriladi.\n"
                "Keyinroq /setadmin orqali o'zgartirishingiz mumkin.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Bazaga saqlash
        sub_id = db.add_subscription(
            user.id,
            bot_id,
            token,
            bot_username,
            bot['name'],
            admin_id
        )
        
        # Botni ishga tushirish
        process = start_bot_instance(token, bot['file'], admin_id)
        
        if process:
            db.update_bot_running(sub_id, 1, process.pid)
            db.add_log(sub_id, "started", f"PID: {process.pid}")
            
            await processing_msg.delete()
            
            # Muvaffaqiyatli xabar
            success_text = f"""
✅ *BOT MUVAFFAQIYATLI ISHGA TUSHIRILDI!*

🤖 *Bot:* @{bot_username}
📦 *Paket:* {bot['name']}
👑 *Admin ID:* `{admin_id}`
📅 *Bepul muddat:* {(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')} gacha
💰 *Narx:* {bot['price']:,} so'm/kun (7 kundan keyin)

🎯 *Endi nima qilish kerak?*
1️⃣ Botingizga o'ting: @{bot_username}
2️⃣ /start buyrug'ini yuboring
3️⃣ Admin panelga kiring
4️⃣ Sozlamalarni o'rnating

📞 *Yordam kerak bo'lsa:* {ADMIN_USERNAME}
            """
            
            await update.message.reply_text(
                success_text,
                reply_markup=get_main_reply_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Admin'ga xabar
            await context.bot.send_message(
                ADMIN_ID,
                f"""
🆕 *YANGI BOT FAOLSHTIRILDI!*

👤 Foydalanuvchi: {user.full_name}
🆔 User ID: `{user.id}`
🤖 Bot: {bot['name']}
🔑 Token: `{token[:20]}...`
👑 Admin ID: `{admin_id}`
📅 Tugash: {(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')}
🔄 PID: {process.pid}

Jarayon monitoring qilinmoqda...
                """,
                parse_mode=ParseMode.MARKDOWN
            )
            
        else:
            db.update_bot_running(sub_id, 0)
            db.add_log(sub_id, "failed", "Process yaratilmadi")
            
            await processing_msg.delete()
            await update.message.reply_text(
                "⚠️ Bot bazaga saqlandi lekin ishga tushmadi.\n"
                "Admin tez orada qo'lda ishga tushiradi.\n\n"
                f"📞 {ADMIN_USERNAME}",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Foydalanuvchi holatini tozalash
        for key in ['activating', 'token', 'bot_username', 'step']:
            if key in context.user_data:
                del context.user_data[key]
        
    except Exception as e:
        await processing_msg.delete()
        logger.error(f"Bot ishga tushirishda xatolik: {e}")
        await update.message.reply_text(
            f"❌ Xatolik yuz berdi: {str(e)[:200]}\n\n"
            f"Admin bilan bog'laning: {ADMIN_USERNAME}",
            parse_mode=ParseMode.MARKDOWN
        )

# ============ BOTNI ISHGA TUSHIRISH ============
def start_bot_instance(token, bot_file, admin_id):
    """Botni alohida jarayonda ishga tushirish (o'lib qolmaydigan)"""
    try:
        bot_path = f"bot_templates/{bot_file}"
        
        if not os.path.exists(bot_path):
            logger.error(f"❌ Bot fayli topilmadi: {bot_path}")
            return None
        
        # Linux (Railway) uchun
        if os.name != 'nt':
            process = subprocess.Popen(
                [sys.executable, bot_path, token, str(admin_id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # O'lib qolmasligi uchun
                preexec_fn=os.setpgrp     # Jarayon guruhini ajratish
            )
        else:
            # Windows uchun
            process = subprocess.Popen(
                [sys.executable, bot_path, token, str(admin_id)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        
        logger.info(f"✅ Bot ishga tushirildi: {bot_file} | PID={process.pid}")
        
        # running_bots lug'atiga qo'shish
        running_bots[id(process)] = {
            'process': process,
            'token': token,
            'file': bot_file,
            'started_at': datetime.now()
        }
        
        return process
        
    except Exception as e:
        logger.error(f"❌ Bot ishga tushirishda xatolik: {e}")
        return None

# ============ BOTLARNI MONITORING QILISH ============
async def monitor_bots():
    """Barcha botlarni monitoring qilish va o'lganlarini qayta ishga tushirish"""
    logger.info("👁 Bot monitoring tizimi ishga tushdi")
    
    while True:
        try:
            active_subs = db.get_all_active_subscriptions()
            
            for sub in active_subs:
                sub_id = sub[0]
                bot_token = sub[3]
                bot_type = sub[2]
                admin_id = sub[5]
                is_running = sub[9]
                pid = sub[13]
                
                # Jarayon ishlayotganini tekshirish
                bot_alive = False
                
                if pid and is_running:
                    try:
                        # PID orqali jarayonni tekshirish
                        os.kill(pid, 0)  # Signal yubormaydi, faqat tekshiradi
                        bot_alive = True
                    except (ProcessLookupError, OSError):
                        bot_alive = False
                    except Exception:
                        bot_alive = False
                
                if not bot_alive:
                    # Bot o'lgan - qayta ishga tushirish
                    bot = BOTS.get(bot_type)
                    if bot:
                        logger.warning(f"🔄 Bot o'lgan, qayta ishga tushirilmoqda: SubID={sub_id}")
                        
                        process = start_bot_instance(bot_token, bot['file'], admin_id)
                        
                        if process:
                            db.update_bot_running(sub_id, 1, process.pid)
                            db.add_log(sub_id, "restarted", f"Qayta ishga tushirildi, PID={process.pid}")
                            logger.info(f"✅ Bot qayta ishga tushirildi: SubID={sub_id}, PID={process.pid}")
                        else:
                            db.update_bot_running(sub_id, 0)
                            db.add_log(sub_id, "restart_failed", "Qayta ishga tushirib bo'lmadi")
                            logger.error(f"❌ Botni qayta ishga tushirib bo'lmadi: SubID={sub_id}")
                            
                            # Admin'ga xabar
                            try:
                                await context.bot.send_message(
                                    ADMIN_ID,
                                    f"⚠️ Bot ishlamayapti!\n"
                                    f"SubID: {sub_id}\n"
                                    f"Bot: {sub[4]}\n"
                                    f"User: {sub[1]}"
                                )
                            except:
                                pass
            
            # Har 60 soniyada tekshirish
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Monitoring xatosi: {e}")
            await asyncio.sleep(10)

# ============ BOSHQA HANDLERLAR ============
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining botlari"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    subs = db.get_user_subscriptions(user_id)
    
    if not subs:
        text = "📦 *Hali botlaringiz yo'q!*\n\nKatalogdan bot tanlang:"
        keyboard = [[InlineKeyboardButton("🛍 KATALOGGA O'TISH", callback_data="catalog")]]
    else:
        text = "📦 *MENING BOTLARIM*\n\n"
        keyboard = []
        
        for sub in subs:
            sub_id = sub[0]
            bot_type = sub[2]
            bot_username = sub[4]
            bot_name = sub[5]
            admin_id = sub[6]
            status = sub[7]
            is_running = sub[9]
            end_date = sub[11]
            
            # Qolgan kunlarni hisoblash
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                days_left = (end - datetime.now()).days
            except:
                days_left = 0
            
            status_emoji = "✅" if is_running else "⚠️"
            status_text = "Ishlayapti" if is_running else "To'xtagan"
            
            text += f"{status_emoji} *{bot_name}*\n"
            text += f"├ 🤖 @{bot_username}\n"
            text += f"├ 👑 Admin: `{admin_id}`\n"
            text += f"├ ⏳ {max(0, days_left)} kun qoldi\n"
            text += f"└ 🔄 {status_text}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ {bot_name[:20]}",
                    callback_data=f"manage_{sub_id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("🛍 YANGI BOT OLISH", callback_data="catalog")])
    
    keyboard.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")])
    
    if query:
        try:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni boshqarish"""
    query = update.callback_query
    await query.answer()
    
    sub_id = int(query.data.replace("manage_", ""))
    sub = db.get_subscription(sub_id)
    
    if not sub or sub[1] != update.effective_user.id:
        await query.edit_message_text("❌ Bot topilmadi!")
        return
    
    text = f"""
⚙️ *BOT BOSHQARUVI*

🤖 *{sub[5]}*
🔗 @{sub[4]}
👑 Admin ID: `{sub[6]}`
📅 Boshlangan: {sub[10][:10]}
⏳ Tugash: {sub[11][:10]}
🔄 Holat: {'Ishlayapti ✅' if sub[9] else 'Toxtagan ⚠️'}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 QAYTA ISHGA TUSHIRISH", callback_data=f"restart_{sub_id}")],
        [InlineKeyboardButton("⏹ TO'XTATISH", callback_data=f"stop_{sub_id}")],
        [InlineKeyboardButton("💰 TO'LOVNI UZAYTIRISH", callback_data=f"renew_{sub_id}")],
        [InlineKeyboardButton("◀️ ORQAGA", callback_data="my_bots")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botni qayta ishga tushirish"""
    query = update.callback_query
    await query.answer()
    
    sub_id = int(query.data.replace("restart_", ""))
    sub = db.get_subscription(sub_id)
    
    if not sub:
        await query.edit_message_text("❌ Bot topilmadi!")
        return
    
    bot_type = sub[2]
    token = sub[3]
    admin_id = sub[6]
    bot = BOTS.get(bot_type)
    
    if bot:
        process = start_bot_instance(token, bot['file'], admin_id)
        if process:
            db.update_bot_running(sub_id, 1, process.pid)
            await query.edit_message_text(
                "✅ Bot qayta ishga tushirildi!",
                reply_markup=get_back_button("my_bots")
            )
        else:
            await query.edit_message_text(
                "❌ Botni ishga tushirib bo'lmadi!",
                reply_markup=get_back_button("my_bots")
            )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kunlik bonus"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    success, amount = db.claim_bonus(user_id)
    
    if success:
        text = f"🎁 *{amount} so'm bonus qo'shildi!*\n\n✅ Har kuni bonus olishingiz mumkin!"
    else:
        text = "⏰ Bugun bonusingizni allaqachon olgansiz!\n\nErtaga yana keling."
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN
        )

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov menyusi"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user = db.get_user(update.effective_user.id)
    balance = user[3] if user else 0
    
    text = f"""
💳 *TO'LOV TIZIMI*

💰 Balans: {balance} so'm

To'lov usullari:
📱 Click: `+998901234567`
💳 Payme: `8600xxxx1234`

To'lov qilib, chekni shu yerga yuboring.
    """
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN
        )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aloqa"""
    query = update.callback_query
    if query:
        await query.answer()
    
    text = f"""
📞 *ALOQA*

Admin: {ADMIN_USERNAME}
Telegram: {ADMIN_USERNAME}

Savollar bo'lsa yozing!
    """
    
    if query:
        await query.edit_message_text(
            text,
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=get_back_button(),
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    query = update.callback_query
    if query:
        await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    stats = db.get_stats()
    
    text = f"""
👑 *ADMIN PANEL*

📊 *Statistika:*
👥 Foydalanuvchilar: {stats['users']}
🤖 Aktiv botlar: {stats['active_bots']}
📦 Jami botlar: {stats['total_bots']}
💰 Bugungi daromad: {stats['today_income']} so'm

🔧 *Boshqaruv:*
    """
    
    keyboard = [
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton("🤖 Barcha botlar", callback_data="admin_all_bots")],
        [InlineKeyboardButton("🔄 O'lgan botlarni tiklash", callback_data="admin_restart_all")],
        [InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_restart_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha o'lgan botlarni qayta ishga tushirish"""
    query = update.callback_query
    await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        return
    
    active_subs = db.get_all_active_subscriptions()
    restarted = 0
    
    for sub in active_subs:
        sub_id = sub[0]
        is_running = sub[9]
        
        if not is_running:
            bot = BOTS.get(sub[2])
            if bot:
                process = start_bot_instance(sub[3], bot['file'], sub[6])
                if process:
                    db.update_bot_running(sub_id, 1, process.pid)
                    restarted += 1
    
    await query.edit_message_text(
        f"✅ {restarted} ta bot qayta ishga tushirildi!",
        reply_markup=get_back_button("admin_panel")
    )

async def cancel_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Faollashtirishni bekor qilish"""
    query = update.callback_query
    await query.answer()
    
    for key in ['activating', 'token', 'bot_username', 'step']:
        if key in context.user_data:
            del context.user_data[key]
    
    await query.edit_message_text(
        "❌ Faollashtirish bekor qilindi.",
        reply_markup=get_back_button("catalog")
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnli xabarlarni qayta ishlash"""
    text = update.message.text
    
    # Token yoki ID kiritish jarayoni
    if context.user_data.get('step') in ['waiting_token', 'waiting_admin_id']:
        await receive_token(update, context)
        return
    
    # Tugmalar
    if text == "🛍 KATALOG":
        await catalog(update, context)
    elif text == "📦 BOTLARIM":
        await my_bots(update, context)
    elif text == "💰 BALANS":
        user = db.get_user(update.effective_user.id)
        bal = user[3] if user else 0
        await update.message.reply_text(
            f"💰 Balans: {bal} so'm",
            reply_markup=get_main_reply_keyboard()
        )
    elif text == "🎁 BONUS":
        await bonus(update, context)
    elif text == "💳 TO'LOV":
        await payment(update, context)
    elif text == "📞 YORDAM":
        await contact(update, context)
    elif text == "/cancel" and context.user_data.get('step'):
        for key in ['activating', 'token', 'bot_username', 'step']:
            if key in context.user_data:
                del context.user_data[key]
        await update.message.reply_text(
            "❌ Bekor qilindi!",
            reply_markup=get_main_reply_keyboard()
        )
    else:
        await update.message.reply_text(
            "Menyudan foydalaning!",
            reply_markup=get_main_inline_keyboard(update.effective_user.id)
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chek rasmini qabul qilish"""
    user_id = update.message.from_user.id
    
    await update.message.reply_text(
        "✅ Chek qabul qilindi!\n"
        f"Admin tez orada tasdiqlaydi.\n"
        f"📞 {ADMIN_USERNAME}"
    )
    
    # Admin'ga forward
    try:
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )
        await context.bot.send_message(
            ADMIN_ID,
            f"💳 To'lov cheki\n👤 User: `{user_id}`",
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatoliklarni ushlash"""
    logger.error(f"Xatolik: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Xatolik yuz berdi. Iltimos qayta urinib ko'ring."
            )
    except:
        pass

# ============ MAIN ============
def main():
    logger.info("="*60)
    logger.info("🚀 BOT STORE UZ - Professional versiya ishga tushmoqda...")
    logger.info(f"🤖 Do'kon boti token: {TOKEN[:15]}...")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info(f"📞 Admin: {ADMIN_USERNAME}")
    logger.info("="*60)
    
    # Papkalarni tekshirish
    if not os.path.exists("bot_templates"):
        os.makedirs("bot_templates")
        logger.warning("⚠️ bot_templates papkasi yaratildi. Bot fayllarini qo'shing!")
    
    # Application yaratish
    app = Application.builder().token(TOKEN).build()
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Callback handlerlar
    app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(bot_info, pattern="^bot_info_"))
    app.add_handler(CallbackQueryHandler(activate_bot, pattern="^activate_"))
    app.add_handler(CallbackQueryHandler(my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(manage_bot, pattern="^manage_"))
    app.add_handler(CallbackQueryHandler(restart_bot, pattern="^restart_"))
    app.add_handler(CallbackQueryHandler(bonus, pattern="^bonus$"))
    app.add_handler(CallbackQueryHandler(payment, pattern="^payment$"))
    app.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_restart_all, pattern="^admin_restart_all$"))
    app.add_handler(CallbackQueryHandler(cancel_activate, pattern="^cancel_activate$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    
    # Message handlerlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    logger.info("✅ Barcha handlerlar yuklandi")
    
    # Bot monitoring thread
    import threading
    monitor_thread = threading.Thread(target=lambda: asyncio.run(monitor_bots()), daemon=True)
    monitor_thread.start()
    logger.info("👁 Bot monitoring tizimi ishga tushdi")
    
    # Sigterm handler
    def handle_sigterm(signum, frame):
        logger.info("⚠️ Bot to'xtatilmoqda...")
        # Barcha botlarni to'xtatish
        for pid, info in running_bots.items():
            try:
                info['process'].terminate()
            except:
                pass
        os._exit(0)
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    
    logger.info("🔥 Bot Store Uz ishga tushdi!")
    
    try:
        app.run_polling(drop_pending_updates=True, close_loop=False)
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Kutilmagan xatolik: {e}")
        # Qayta ishga tushirish
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
