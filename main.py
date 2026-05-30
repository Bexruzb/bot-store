import sqlite3
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"

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
                joined_date TEXT
            );
            
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_type TEXT,
                bot_token TEXT,
                bot_username TEXT,
                bot_name TEXT,
                admin_id INTEGER,
                status TEXT DEFAULT 'trial',
                start_date TEXT,
                end_date TEXT,
                price INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS bot_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sub_id INTEGER,
                pid INTEGER,
                is_running INTEGER DEFAULT 1
            );
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, username, full_name):
        self.c.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, joined_date) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, datetime.now().isoformat())
        )
        self.conn.commit()
    
    def get_user(self, user_id):
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()
    
    def add_balance(self, user_id, amount):
        self.c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def add_subscription(self, user_id, bot_type, bot_token, bot_username, bot_name, admin_id, price):
        start = datetime.now()
        end = start + timedelta(days=7)
        self.c.execute('''
            INSERT INTO subscriptions 
            (user_id, bot_type, bot_token, bot_username, bot_name, admin_id, start_date, end_date, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, bot_type, bot_token, bot_username, bot_name, admin_id, start.isoformat(), end.isoformat(), price))
        self.conn.commit()
        return self.c.lastrowid
    
    def get_user_subscriptions(self, user_id):
        self.c.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status IN ('trial', 'active')", (user_id,))
        return self.c.fetchall()

db = Database()

# ============ 5 TA KUCHLI BOTLAR ============
BOTS = {
    "shop": {
        "name": "🛍 Mini Do'kon Boti",
        "icon": "🛍",
        "desc": """
📦 *Afzalliklari:*
• Mahsulotlar katalogi
• Savatcha tizimi
• Buyurtma qabul qilish
• Admin panel
• Statistika

👥 *Kimlar uchun:*
Do'kon egalari, tadbirkorlar
        """,
        "file": "shop_bot.py",
        "price": 10000,
        "category": "Biznes"
    },
    "admin": {
        "name": "📊 Guruh Boshqaruv Boti",
        "icon": "📊",
        "desc": """
🛡 *Afzalliklari:*
• Spam filtr
• Avtomatik ban
• Xush kelibsiz xabari
• Statistika
• Reklama o'chirish

👥 *Kimlar uchun:*
Guruh adminlari
        """,
        "file": "admin_bot.py",
        "price": 8000,
        "category": "Boshqaruv"
    },
    "quiz": {
        "name": "🎮 Viktorina Boti",
        "icon": "🎮",
        "desc": """
🎯 *Afzalliklari:*
• Test yaratish
• Reyting tizimi
• Mukofot berish
• Natijalar
• 10+ til

👥 *Kimlar uchun:*
O'qituvchilar, HR
        """,
        "file": "quiz_bot.py",
        "price": 5000,
        "category": "Ta'lim"
    },
    "reminder": {
        "name": "📝 Eslatma Boti",
        "icon": "📝",
        "desc": """
⏰ *Afzalliklari:*
• Vazifa eslatmalari
• Takroriy eslatmalar
• Ovozli eslatma
• Kalendar integratsiyasi

👥 *Kimlar uchun:*
Hamma foydalanuvchilar
        """,
        "file": "reminder_bot.py",
        "price": 3000,
        "category": "Produktivlik"
    },
    "weather": {
        "name": "🌤 Ob-havo Boti",
        "icon": "🌤",
        "desc": """
🌍 *Afzalliklari:*
• Barcha shaharlar
• 7 kunlik prognoz
• GPS orqali aniqlash
• Ob-havo xaritasi

👥 *Kimlar uchun:*
Hamma foydalanuvchilar
        """,
        "file": "weather_bot.py",
        "price": 1000,
        "category": "Ma'lumot"
    }
}

# ============ ASOSIY MENYU ============
def get_main_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS", callback_data="balance")],
        [InlineKeyboardButton("🎁 BONUS", callback_data="bonus")],
        [InlineKeyboardButton("📞 ALOQA", callback_data="contact")]
    ])

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.full_name)
    
    # To'g'ridan-to'g'ri inline menyu
    await update.message.reply_text(
        f"""
🤖 *BOT STORE UZ* ga xush kelibsiz!

👋 Salom, {user.first_name}!

🔥 *5 ta professional bot*
✅ *7 kun BEPUL sinov*
💎 *Sifat kafolati*

💰 Narxlar: 1 000 - 10 000 so'm

⚡️ Quyidagi menyudan foydalaning:
        """,
        reply_markup=get_main_inline(),
        parse_mode=ParseMode.MARKDOWN
    )

# ============ KATALOG ============
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n"
    text += "🔥 Sifatli botlar | 7 kun BEPUL\n\n"
    
    keyboard = []
    for bot_id, bot in BOTS.items():
        text += f"{bot['icon']} *{bot['name']}*\n"
        text += f"💰 {bot['price']:,} so'm/kun\n"
        text += f"📂 {bot['category']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{bot['icon']} {bot['name']} | {bot['price']:,} so'm",
                callback_data=f"info_{bot_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")])
    
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

# ============ BOT HAQIDA ============
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("info_", "")
    bot = BOTS.get(bot_id)
    
    if not bot:
        return
    
    text = f"""
*{bot['icon']} {bot['name']}*

{bot['desc']}

💰 *Narx:* {bot['price']:,} so'm/kun
🆓 *Bepul:* 7 kun

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

# ============ FAOLSHTIRISH ============
async def activate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("activate_", "")
    bot = BOTS.get(bot_id)
    
    context.user_data['activating'] = bot_id
    context.user_data['step'] = 'waiting_token'
    
    text = f"""
🔑 *{bot['name']}* ni faollashtirish

*1-QADAM: Bot yarating*

@BotFather'ga o'ting:
• /newbot yozing
• Bot nomini kiriting
• Username kiriting

Olingan *TOKEN* ni yuboring!

❌ Bekor qilish: /cancel
    """
    
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN
    )

# ============ TOKEN QABUL QILISH ============
async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'activating' not in context.user_data:
        return
    
    step = context.user_data.get('step', 'waiting_token')
    
    if step == 'waiting_token':
        token = update.message.text.strip()
        
        if ':' not in token:
            await update.message.reply_text("❌ Noto'g'ri token! @BotFather'dan olingan tokenni yuboring.")
            return
        
        # Tokenni tekshirish
        processing = await update.message.reply_text("⏳ Token tekshirilmoqda...")
        
        try:
            test_bot = Bot(token=token)
            bot_info = await test_bot.get_me()
            
            context.user_data['token'] = token
            context.user_data['bot_username'] = bot_info.username
            context.user_data['step'] = 'waiting_admin_id'
            
            await processing.delete()
            
            bot = BOTS.get(context.user_data['activating'])
            
            await update.message.reply_text(
                f"✅ Token qabul qilindi!\n"
                f"🤖 @{bot_info.username}\n\n"
                f"*2-QADAM: Admin ID'ni kiriting*\n\n"
                f"@userinfobot ga /start yozing va ID'ngizni oling.\n"
                f"So'ng shu yerga yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await processing.delete()
            await update.message.reply_text(
                "❌ Token noto'g'ri! @BotFather'dan yangi token oling."
            )
    
    elif step == 'waiting_admin_id':
        try:
            admin_id = int(update.message.text.strip())
            
            # ID'ni tekshirish
            try:
                await context.bot.send_chat_action(chat_id=admin_id, action="typing")
            except:
                await update.message.reply_text(
                    "❌ Noto'g'ri ID! Bot bu ID'ga xabar yubora olmaydi.\n"
                    "Iltimos, to'g'ri ID kiriting."
                )
                return
            
            bot_id = context.user_data['activating']
            token = context.user_data['token']
            bot_username = context.user_data['bot_username']
            bot = BOTS.get(bot_id)
            
            # Bazaga saqlash
            sub_id = db.add_subscription(
                update.message.from_user.id,
                bot_id,
                token,
                bot_username,
                bot['name'],
                admin_id,
                bot['price']
            )
            
            # Botni ishga tushirish
            bot_file = bot.get('file')
            start_bot_instance(token, bot_file, admin_id)
            
            # Tozalash
            del context.user_data['activating']
            del context.user_data['token']
            del context.user_data['bot_username']
            del context.user_data['step']
            
            await update.message.reply_text(
                f"""
✅ *BOT FAOLSHTIRILDI!*

🤖 @{bot_username}
📦 {bot['name']}
👑 Admin: {admin_id}
📅 Bepul: {(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')} gacha

🎯 *Endi nima qilish kerak?*
1. Botingizga /start yuboring
2. Admin panelga kiring
3. Sozlamalarni o'rnating

📞 Yordam: {ADMIN_USERNAME}
                """,
                reply_markup=get_main_inline(),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except ValueError:
            await update.message.reply_text("❌ ID faqat raqamlardan iborat bo'lishi kerak!")

# ============ BOTNI ISHGA TUSHIRISH ============
def start_bot_instance(token, bot_file, admin_id):
    try:
        bot_path = f"bot_templates/{bot_file}"
        if os.path.exists(bot_path):
            process = subprocess.Popen(
                [sys.executable, bot_path, token, str(admin_id)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            logger.info(f"✅ Bot ishga tushirildi: {token[:15]}... Admin: {admin_id}")
            return process
    except Exception as e:
        logger.error(f"❌ Bot ishga tushirishda xatolik: {e}")

# ============ BOSHQA HANDLERLAR ============
async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    subs = db.get_user_subscriptions(user_id)
    
    if not subs:
        text = "📦 Hali botlaringiz yo'q!"
        keyboard = [[InlineKeyboardButton("🛍 Katalogga o'tish", callback_data="catalog")]]
    else:
        text = "📦 *MENING BOTLARIM*\n\n"
        for sub in subs:
            try:
                end = datetime.fromisoformat(sub[8])
                days = (end - datetime.now()).days
                status = "✅" if days > 0 else "⚠️"
                text += f"{status} {sub[6]}\n"
                text += f"⏳ {max(0, days)} kun\n"
                text += f"👑 Admin ID: {sub[5]}\n"
                text += f"🔗 @{sub[4]}\n\n"
            except:
                pass
        keyboard = [
            [InlineKeyboardButton("🛍 Yangi bot", callback_data="catalog")],
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
        ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(update.effective_user.id)
    bal = user[3] if user else 0
    
    await query.edit_message_text(
        f"💰 Balans: {bal} so'm\n\n"
        f"💳 To'ldirish uchun: {ADMIN_USERNAME}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
        ])
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    db.add_balance(update.effective_user.id, 100)
    
    await query.edit_message_text(
        "🎁 100 so'm bonus qo'shildi!\n\n"
        "Har kuni bonus olishingiz mumkin!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
        ])
    )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        f"📞 *Aloqa*\n\n"
        f"Admin: {ADMIN_USERNAME}\n"
        f"Telegram: {ADMIN_USERNAME}\n\n"
        f"Savollar bo'lsa yozing!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 BOSH MENYU", callback_data="main_menu")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📋 *Bosh Menyu*",
        reply_markup=get_main_inline(),
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'activating' in context.user_data:
        del context.user_data['activating']
        if 'token' in context.user_data:
            del context.user_data['token']
        if 'step' in context.user_data:
            del context.user_data['step']
    
    await update.message.reply_text(
        "❌ Bekor qilindi!",
        reply_markup=get_main_inline()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'activating' in context.user_data:
        await receive_token(update, context)
    else:
        await update.message.reply_text(
            "Menyudan foydalaning yoki /start yozing!",
            reply_markup=get_main_inline()
        )

# ============ MAIN ============
def main():
    # Papkalarni yaratish
    os.makedirs("bot_templates", exist_ok=True)
    
    logger.info("🚀 BOT STORE UZ - Professional versiya")
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(bot_info, pattern="^info_"))
    app.add_handler(CallbackQueryHandler(activate_bot, pattern="^activate_"))
    app.add_handler(CallbackQueryHandler(my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(bonus, pattern="^bonus$"))
    app.add_handler(CallbackQueryHandler(contact, pattern="^contact$"))
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Barcha handlerlar yuklandi")
    logger.info("🔥 5 ta kuchli bot bilan ishga tushdi!")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
