"""
🤖 BOT STORE UZ - Professional Do'kon Boti
Barcha xatoliklar tuzatilgan FULL versiya
Token + Admin ID so'rash | Bot monitoring | 24/7 ishlash
"""

import sqlite3
import logging
import os
import subprocess
import sys
import asyncio
import signal
import time
import threading
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ KONFIGURATSIYA ============
TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

# ============ BOT JARAYONLARI ============
running_bots = {}

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
                joined_date TEXT,
                total_bots INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_type TEXT,
                bot_token TEXT UNIQUE,
                bot_username TEXT,
                bot_name TEXT,
                admin_id INTEGER,
                status TEXT DEFAULT 'trial',
                is_running INTEGER DEFAULT 0,
                start_date TEXT,
                end_date TEXT,
                price INTEGER DEFAULT 0,
                pid INTEGER DEFAULT 0
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
            "INSERT OR IGNORE INTO users (user_id, username, full_name, joined_date) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
    
    def add_subscription(self, user_id, bot_type, bot_token, bot_username, bot_name, admin_id, price):
        start = datetime.now()
        end = start + timedelta(days=7)
        self.execute('''
            INSERT INTO subscriptions 
            (user_id, bot_type, bot_token, bot_username, bot_name, admin_id, start_date, end_date, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, bot_type, bot_token, bot_username, bot_name, admin_id,
              start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'), price))
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
        return {
            'users': self.fetchone("SELECT COUNT(*) FROM users")[0],
            'active_bots': self.fetchone("SELECT COUNT(*) FROM subscriptions WHERE status IN ('trial', 'active')")[0],
            'total_bots': self.fetchone("SELECT COUNT(*) FROM subscriptions")[0]
        }

db = Database()

# ============ 5 TA BOTLAR KATALOGI ============
BOTS = {
    "shop": {
        "name": "🛍 Mini Do'kon Boti",
        "icon": "🛍",
        "desc": "📦 Mahsulotlar katalogi\n🛒 Savatcha tizimi\n👑 Admin panel\n📊 Statistika",
        "file": "shop_bot.py",
        "price": 10000,
        "category": "💼 Biznes"
    },
    "admin": {
        "name": "📊 Guruh Boshqaruv Boti",
        "icon": "📊",
        "desc": "🛡 Spam filtr\n🚫 Avto-ban tizimi\n👋 Xush kelibsiz\n📊 Statistika",
        "file": "admin_bot.py",
        "price": 8000,
        "category": "👥 Hamjamiyat"
    },
    "quiz": {
        "name": "🎮 Viktorina Boti",
        "icon": "🎮",
        "desc": "🎯 Test yaratish\n🏆 Reyting tizimi\n🎁 Mukofotlar\n📊 Natijalar",
        "file": "quiz_bot.py",
        "price": 5000,
        "category": "📚 Ta'lim"
    },
    "reminder": {
        "name": "📝 Eslatma Boti",
        "icon": "📝",
        "desc": "⏰ Vazifa eslatmalari\n🔄 Takroriy eslatmalar\n🎤 Ovozli eslatma\n📅 Kalendar",
        "file": "reminder_bot.py",
        "price": 3000,
        "category": "📋 Produktivlik"
    },
    "weather": {
        "name": "🌤 Ob-havo Boti",
        "icon": "🌤",
        "desc": "🌍 Barcha shaharlar\n📊 7 kunlik prognoz\n📍 GPS aniqlash\n🗺 Ob-havo xaritasi",
        "file": "weather_bot.py",
        "price": 1000,
        "category": "🌍 Ma'lumot"
    }
}

# ============ KEYBOARDLAR ============
def get_main_reply_keyboard():
    return ReplyKeyboardMarkup([
        ["🛍 KATALOG", "📦 BOTLARIM"],
        ["💰 BALANS", "🎁 BONUS"],
        ["💳 TO'LOV", "📞 YORDAM"]
    ], resize_keyboard=True)

def get_main_inline_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="payment")],
        [InlineKeyboardButton("🎁 KUNLIK BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_back_button(callback_data="main_menu"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ ORQAGA", callback_data=callback_data)],
        [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
    ])

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db.add_user(user.id, user.username, user.full_name)
        
        welcome = f"""
🤖 *BOT STORE UZ* ga xush kelibsiz!

👋 Salom, *{user.first_name}*!

🔥 *5 ta professional bot*
✅ *7 kun BEPUL sinov*
💰 *1 000 - 10 000 so'm/kun*
🛡 *24/7 ishlash kafolati*
        """
        
        if update.message:
            await update.message.reply_text(
                welcome,
                reply_markup=get_main_reply_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            await update.message.reply_text(
                "📋 *Menyu:*",
                reply_markup=get_main_inline_keyboard(user.id),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            query = update.callback_query
            await query.edit_message_text(
                welcome,
                reply_markup=get_main_inline_keyboard(user.id),
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logger.error(f"Start xatosi: {e}")

# ============ KATALOG ============
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query:
            await query.answer()
        
        text = "🎯 *BOTLAR KATALOGI*\n\n🔥 Barchasi 7 kun BEPUL!\n\n"
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
            await query.edit_message_text(
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
    except Exception as e:
        logger.error(f"Catalog xatosi: {e}")

# ============ BOT HAQIDA ============
async def show_bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id):
    try:
        query = update.callback_query
        bot = BOTS.get(bot_id)
        
        if not bot:
            await query.edit_message_text("❌ Bot topilmadi!", reply_markup=get_back_button())
            return
        
        text = f"""
*{bot['icon']} {bot['name']}*

{bot['desc']}

💰 *Narx:* {bot['price']:,} so'm/kun
🆓 *Bepul sinov:* 7 kun

⚡️ Tanlang:
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
    except Exception as e:
        logger.error(f"Bot info xatosi: {e}")

# ============ FAOLSHTIRISH BOSHLASH ============
async def activate_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id):
    try:
        query = update.callback_query
        bot = BOTS.get(bot_id)
        
        if not bot:
            await query.edit_message_text("❌ Bot topilmadi!")
            return
        
        context.user_data['activating'] = bot_id
        context.user_data['step'] = 'waiting_token'
        
        text = f"""
🔑 *{bot['name']}* - FAOLSHTIRISH

*1-QADAM: Token oling*

📱 @BotFather'ga o'ting:
1️⃣ /newbot yozing
2️⃣ Bot nomini kiriting
3️⃣ Username kiriting
4️⃣ TOKENni shu yerga yuboring

❌ Bekor qilish: /cancel
        """
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="cancel_activate")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Activate start xatosi: {e}")

# ============ TOKEN QABUL QILISH ============
async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        # Token formatini tekshirish
        if ':' not in text or len(text) < 45:
            await update.message.reply_text(
                "❌ Noto'g'ri token formati!\n@BotFather'dan /newbot orqali token oling."
            )
            return
        
        # Token mavjudligini tekshirish
        if db.check_token_exists(text):
            await update.message.reply_text(
                "❌ Bu token allaqachon ishlatilgan!\nYangi bot yarating."
            )
            return
        
        processing = await update.message.reply_text("⏳ Token tekshirilmoqda...")
        
        try:
            test_bot = Bot(token=text)
            bot_info = await test_bot.get_me()
            
            context.user_data['token'] = text
            context.user_data['bot_username'] = bot_info.username
            context.user_data['step'] = 'waiting_admin_id'
            
            await processing.delete()
            
            await update.message.reply_text(
                f"✅ Token qabul qilindi!\n"
                f"🤖 @{bot_info.username}\n\n"
                f"*2-QADAM: Admin ID'ni kiriting*\n\n"
                f"@userinfobot ga /start yozing va ID oling.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await processing.delete()
            await update.message.reply_text(
                "❌ Token noto'g'ri yoki eskirgan!\n@BotFather'dan yangi token oling."
            )
            
    except Exception as e:
        logger.error(f"Receive token xatosi: {e}")

# ============ ADMIN ID QABUL QILISH ============
async def receive_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        try:
            admin_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ ID faqat raqamlardan iborat bo'lishi kerak!")
            return
        
        if admin_id <= 0:
            await update.message.reply_text("❌ Noto'g'ri ID!")
            return
        
        processing = await update.message.reply_text("⏳ Bot ishga tushirilmoqda...")
        
        bot_id = context.user_data['activating']
        token = context.user_data['token']
        bot_username = context.user_data['bot_username']
        bot = BOTS.get(bot_id)
        
        # Bazaga saqlash
        sub_id = db.add_subscription(
            user.id, bot_id, token, bot_username, bot['name'], admin_id, bot['price']
        )
        
        # Botni ishga tushirish
        process = start_bot_instance(token, bot['file'], admin_id)
        
        if process:
            db.update_bot_running(sub_id, 1, process.pid)
            db.add_log(sub_id, "started", f"PID: {process.pid}")
            
            await processing.delete()
            
            success_text = f"""
✅ *BOT ISHGA TUSHIRILDI!*

🤖 @{bot_username}
📦 {bot['name']}
👑 Admin ID: `{admin_id}`
📅 Bepul: {(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')} gacha
💰 Narx: {bot['price']:,} so'm/kun

Botingizga o'ting: @{bot_username}
            """
            
            await update.message.reply_text(
                success_text,
                reply_markup=get_main_reply_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Admin'ga xabar
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"🆕 Yangi bot!\n👤 {user.full_name}\n"
                    f"🤖 {bot['name']}\n👑 Admin: {admin_id}",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        else:
            await processing.delete()
            await update.message.reply_text(
                "⚠️ Bot saqlandi lekin ishga tushmadi.\nAdmin tez orada qo'lda ishga tushiradi."
            )
        
        # Tozalash
        for key in ['activating', 'token', 'bot_username', 'step']:
            if key in context.user_data:
                del context.user_data[key]
                
    except Exception as e:
        logger.error(f"Receive admin id xatosi: {e}")
        await update.message.reply_text(f"❌ Xatolik: {str(e)[:200]}")

# ============ BOTNI ISHGA TUSHIRISH ============
def start_bot_instance(token, bot_file, admin_id):
    try:
        bot_path = f"bot_templates/{bot_file}"
        
        if not os.path.exists(bot_path):
            logger.error(f"Bot fayli topilmadi: {bot_path}")
            return None
        
        if os.name != 'nt':
            process = subprocess.Popen(
                [sys.executable, bot_path, token, str(admin_id)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                preexec_fn=os.setpgrp
            )
        else:
            process = subprocess.Popen(
                [sys.executable, bot_path, token, str(admin_id)],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        
        running_bots[id(process)] = {
            'process': process,
            'token': token,
            'file': bot_file,
            'started_at': datetime.now()
        }
        
        logger.info(f"✅ Bot ishga tushdi: {bot_file} PID={process.pid}")
        return process
        
    except Exception as e:
        logger.error(f"Bot ishga tushirish xatosi: {e}")
        return None

# ============ BOT MONITORING ============
async def monitor_bots():
    logger.info("👁 Monitoring boshlandi")
    
    while True:
        try:
            active_subs = db.get_all_active_subscriptions()
            
            for sub in active_subs:
                sub_id = sub[0]
                is_running = sub[9]
                pid = sub[13]
                
                bot_alive = False
                if pid and is_running:
                    try:
                        os.kill(pid, 0)
                        bot_alive = True
                    except:
                        bot_alive = False
                
                if not bot_alive:
                    bot = BOTS.get(sub[2])
                    if bot:
                        logger.warning(f"🔄 Bot qayta ishga tushirilmoqda: SubID={sub_id}")
                        process = start_bot_instance(sub[3], bot['file'], sub[6])
                        if process:
                            db.update_bot_running(sub_id, 1, process.pid)
                            db.add_log(sub_id, "restarted", f"PID={process.pid}")
            
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Monitoring xatosi: {e}")
            await asyncio.sleep(10)

# ============ MENING BOTLARIM ============
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query:
            await query.answer()
        
        user_id = update.effective_user.id
        subs = db.get_user_subscriptions(user_id)
        
        if not subs:
            text = "📦 Hali botlaringiz yo'q!"
            keyboard = [[InlineKeyboardButton("🛍 KATALOG", callback_data="catalog")]]
        else:
            text = "📦 *MENING BOTLARIM*\n\n"
            keyboard = []
            
            for sub in subs:
                try:
                    end = datetime.strptime(sub[11], '%Y-%m-%d %H:%M:%S')
                    days = (end - datetime.now()).days
                except:
                    days = 0
                
                status = "✅" if sub[9] else "⚠️"
                text += f"{status} *{sub[5]}*\n"
                text += f"├ 🤖 @{sub[4]}\n"
                text += f"├ 👑 `{sub[6]}`\n"
                text += f"├ ⏳ {max(0, days)} kun\n"
                text += f"└ 💰 {sub[12]} so'm/kun\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(f"⚙️ {sub[5][:20]}", callback_data=f"manage_{sub[0]}")
                ])
            
            keyboard.append([InlineKeyboardButton("🛍 YANGI BOT", callback_data="catalog")])
        
        keyboard.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")])
        
        if query:
            await query.edit_message_text(
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
    except Exception as e:
        logger.error(f"My bots xatosi: {e}")

# ============ BOT BOSHQARUVI ============
async def manage_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        sub_id = int(query.data.replace("manage_", ""))
        sub = db.get_subscription(sub_id)
        
        if not sub:
            await query.edit_message_text("❌ Bot topilmadi!")
            return
        
        try:
            end = datetime.strptime(sub[11], '%Y-%m-%d %H:%M:%S')
            days = (end - datetime.now()).days
        except:
            days = 0
        
        text = f"""
⚙️ *BOT BOSHQARUVI*

🤖 {sub[5]}
🔗 @{sub[4]}
👑 Admin: `{sub[6]}`
📅 Boshlangan: {sub[10][:10]}
⏳ Tugash: {sub[11][:10]}
⏰ Qolgan: {max(0, days)} kun
🔄 Holat: {'Ishlayapti ✅' if sub[9] else 'Toxtagan ⚠️'}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 QAYTA ISHGA TUSHIRISH", callback_data=f"restart_{sub_id}")],
            [InlineKeyboardButton("⏹ TO'XTATISH", callback_data=f"stop_{sub_id}")],
            [InlineKeyboardButton("💰 UZAYTIRISH", callback_data=f"renew_{sub_id}")],
            [InlineKeyboardButton("◀️ ORQAGA", callback_data="my_bots")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Manage bot xatosi: {e}")

# ============ BOTNI QAYTA ISHGA TUSHIRISH ============
async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        sub_id = int(query.data.replace("restart_", ""))
        sub = db.get_subscription(sub_id)
        
        if not sub:
            await query.edit_message_text("❌ Bot topilmadi!")
            return
        
        bot = BOTS.get(sub[2])
        if bot:
            process = start_bot_instance(sub[3], bot['file'], sub[6])
            if process:
                db.update_bot_running(sub_id, 1, process.pid)
                await query.edit_message_text(
                    "✅ Bot qayta ishga tushirildi!",
                    reply_markup=get_back_button("my_bots")
                )
            else:
                await query.edit_message_text(
                    "❌ Ishga tushirib bo'lmadi!",
                    reply_markup=get_back_button("my_bots")
                )
    except Exception as e:
        logger.error(f"Restart bot xatosi: {e}")

# ============ BOTNI TO'XTATISH ============
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        sub_id = int(query.data.replace("stop_", ""))
        db.update_subscription_status(sub_id, 'stopped')
        db.update_bot_running(sub_id, 0)
        
        await query.edit_message_text(
            "⏹ Bot to'xtatildi.",
            reply_markup=get_back_button("my_bots")
        )
    except Exception as e:
        logger.error(f"Stop bot xatosi: {e}")

# ============ TO'LOV UZAYTIRISH ============
async def renew_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        sub_id = int(query.data.replace("renew_", ""))
        sub = db.get_subscription(sub_id)
        
        if not sub:
            await query.edit_message_text("❌ Bot topilmadi!")
            return
        
        price = sub[12]
        
        text = f"""
💰 *TO'LOV UZAYTIRISH*

Bot: {sub[5]}
Narx: {price:,} so'm/kun

To'lov usullari:
📱 Click: +998704785888
💳 Payme: 9860 0825 1273 7923

To'lov qilib, chekni yuboring.
        """
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button(f"manage_{sub_id}"),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Renew bot xatosi: {e}")

# ============ SOTIB OLISH ============
async def buy_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        bot_id = query.data.replace("buy_", "")
        bot = BOTS.get(bot_id)
        
        if not bot:
            await query.edit_message_text("❌ Bot topilmadi!")
            return
        
        text = f"""
💳 *{bot['name']}* - SOTIB OLISH

Narx: {bot['price']:,} so'm/kun

To'lov usullari:
📱 Click: +998704785888
💳 Payme: 9860 0825 1273 7923

To'lov qilib, chekni yuboring.
Admin 24 soat ichida faollashtiradi.
        """
        
        await query.edit_message_text(
            text,
            reply_markup=get_back_button(f"bot_info_{bot_id}"),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Buy bot xatosi: {e}")

# ============ BONUS ============
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query:
            await query.answer()
        
        user_id = update.effective_user.id
        success, amount = db.claim_bonus(user_id)
        
        text = f"🎁 {amount} so'm bonus qo'shildi!" if success else "⏰ Bugun bonusingizni olgansiz!"
        
        if query:
            await query.edit_message_text(text, reply_markup=get_back_button())
        else:
            await update.message.reply_text(text, reply_markup=get_back_button())
    except Exception as e:
        logger.error(f"Bonus xatosi: {e}")

# ============ TO'LOV ============
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query:
            await query.answer()
        
        user = db.get_user(update.effective_user.id)
        balance = user[3] if user else 0
        
        text = f"""
💳 *TO'LOV*

💰 Balans: {balance} so'm

To'lov usullari:
📱 Click: +998704785888
💳 Payme: 9860 0825 1273 7923

To'lov qilib, chekni yuboring.
        """
        
        if query:
            await query.edit_message_text(text, reply_markup=get_back_button(), parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(text, reply_markup=get_back_button(), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"Payment xatosi: {e}")

# ============ ALOQA ============
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        if query:
            await query.answer()
        
        text = f"📞 Admin: {ADMIN_USERNAME}\n\nSavollar bo'lsa yozing!"
        
        if query:
            await query.edit_message_text(text, reply_markup=get_back_button())
        else:
            await update.message.reply_text(text, reply_markup=get_back_button())
    except Exception as e:
        logger.error(f"Contact xatosi: {e}")

# ============ ADMIN PANEL ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if update.effective_user.id != ADMIN_ID:
            return
        
        stats = db.get_stats()
        
        text = f"""
👑 *ADMIN PANEL*

👥 Foydalanuvchilar: {stats['users']}
🤖 Aktiv botlar: {stats['active_bots']}
📦 Jami botlar: {stats['total_bots']}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 O'LGAN BOTLARNI TIKLASH", callback_data="admin_restart_all")],
            [InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Admin panel xatosi: {e}")

# ============ BARCHA BOTLARNI TIKLASH ============
async def admin_restart_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if update.effective_user.id != ADMIN_ID:
            return
        
        active_subs = db.get_all_active_subscriptions()
        restarted = 0
        
        for sub in active_subs:
            if not sub[9]:
                bot = BOTS.get(sub[2])
                if bot:
                    process = start_bot_instance(sub[3], bot['file'], sub[6])
                    if process:
                        db.update_bot_running(sub[0], 1, process.pid)
                        restarted += 1
        
        await query.edit_message_text(
            f"✅ {restarted} ta bot qayta ishga tushirildi!",
            reply_markup=get_back_button("admin_panel")
        )
    except Exception as e:
        logger.error(f"Admin restart xatosi: {e}")

# ============ BEKOR QILISH ============
async def cancel_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        for key in ['activating', 'token', 'bot_username', 'step']:
            if key in context.user_data:
                del context.user_data[key]
        
        await query.edit_message_text(
            "❌ Bekor qilindi.",
            reply_markup=get_back_button("catalog")
        )
    except Exception as e:
        logger.error(f"Cancel xatosi: {e}")

# ============ CALLBACK HANDLER ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """BARCHA callback query'larni qayta ishlash"""
    query = update.callback_query
    data = query.data
    
    try:
        await query.answer()
    except:
        pass
    
    try:
        if data == "main_menu":
            await start(update, context)
        elif data == "catalog":
            await catalog(update, context)
        elif data == "my_bots":
            await my_bots(update, context)
        elif data == "bonus":
            await bonus(update, context)
        elif data == "payment":
            await payment(update, context)
        elif data == "contact":
            await contact(update, context)
        elif data == "admin_panel":
            await admin_panel(update, context)
        elif data == "admin_restart_all":
            await admin_restart_all(update, context)
        elif data == "cancel_activate":
            await cancel_activate(update, context)
        elif data.startswith("bot_info_"):
            await show_bot_info(update, context, data.replace("bot_info_", ""))
        elif data.startswith("activate_"):
            await activate_bot_start(update, context, data.replace("activate_", ""))
        elif data.startswith("buy_"):
            await buy_bot(update, context)
        elif data.startswith("manage_"):
            await manage_bot(update, context)
        elif data.startswith("restart_"):
            await restart_bot(update, context)
        elif data.startswith("stop_"):
            await stop_bot(update, context)
        elif data.startswith("renew_"):
            await renew_bot(update, context)
        else:
            logger.warning(f"Noma'lum callback: {data}")
    except Exception as e:
        logger.error(f"Button handler xatosi [{data}]: {e}")
        try:
            await query.edit_message_text(
                "⚠️ Xatolik yuz berdi. Bosh menyuga qayting.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
                ])
            )
        except:
            pass

# ============ TEXT HANDLER ============
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        user = update.effective_user
        
        # Token/ID kiritish jarayoni
        if context.user_data.get('step') == 'waiting_token':
            await receive_token(update, context)
            return
        elif context.user_data.get('step') == 'waiting_admin_id':
            await receive_admin_id(update, context)
            return
        
        # Menyu tugmalari
        if text == "🛍 KATALOG":
            await catalog(update, context)
        elif text == "📦 BOTLARIM":
            await my_bots(update, context)
        elif text == "💰 BALANS":
            bal = db.get_user(user.id)
            await update.message.reply_text(
                f"💰 Balans: {bal[3] if bal else 0} so'm",
                reply_markup=get_main_reply_keyboard()
            )
        elif text == "🎁 BONUS":
            await bonus(update, context)
        elif text == "💳 TO'LOV":
            await payment(update, context)
        elif text == "📞 YORDAM":
            await contact(update, context)
        elif text == "/cancel":
            for key in ['activating', 'token', 'bot_username', 'step']:
                if key in context.user_data:
                    del context.user_data[key]
            await update.message.reply_text("❌ Bekor qilindi!", reply_markup=get_main_reply_keyboard())
        else:
            await update.message.reply_text(
                "Menyudan foydalaning!",
                reply_markup=get_main_inline_keyboard(user.id)
            )
    except Exception as e:
        logger.error(f"Handle text xatosi: {e}")

# ============ PHOTO HANDLER ============
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        await update.message.reply_text("✅ Chek qabul qilindi!")
        
        try:
            await context.bot.forward_message(ADMIN_ID, user_id, update.message.message_id)
            await context.bot.send_message(ADMIN_ID, f"💳 Chek | User: `{user_id}`", parse_mode=ParseMode.MARKDOWN)
        except:
            pass
    except Exception as e:
        logger.error(f"Photo handler xatosi: {e}")

# ============ ERROR HANDLER ============
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xatolik: {context.error}")

# ============ MAIN ============
def main():
    logger.info("="*50)
    logger.info("🚀 BOT STORE UZ ishga tushmoqda...")
    logger.info(f"👑 Admin: {ADMIN_ID}")
    logger.info("="*50)
    
    if not os.path.exists("bot_templates"):
        os.makedirs("bot_templates")
    
    app = Application.builder().token(TOKEN).build()
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Callback handler - FAQAT BITTA!
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlerlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    # Monitoring thread
    def run_monitoring():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(monitor_bots())
    
    monitor_thread = threading.Thread(target=run_monitoring, daemon=True)
    monitor_thread.start()
    logger.info("👁 Monitoring ishga tushdi")
    
    # Signal handler
    def handle_signal(signum, frame):
        logger.info("Bot to'xtatilmoqda...")
        os._exit(0)
    
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    logger.info("🔥 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
