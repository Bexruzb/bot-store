import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ============ SOZLAMALAR ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930
ADMIN_USERNAME = "@yoldoshev_3"  # To'g'rilandi!

# ============ DATABASE ============
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('botstore.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.init_tables()
    
    def init_tables(self):
        self.c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance INTEGER DEFAULT 0,
                bonus_claimed TEXT,
                joined_date TEXT
            );
            
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_type TEXT,
                bot_token TEXT,
                bot_username TEXT,
                bot_name TEXT,
                status TEXT DEFAULT 'active',
                is_running INTEGER DEFAULT 0,
                start_date TEXT,
                end_date TEXT,
                daily_price INTEGER DEFAULT 300
            );
            
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                date TEXT
            );
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, username, full_name):
        self.c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, joined_date) VALUES (?, ?, ?, ?)",
                       (user_id, username, full_name, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_user(self, user_id):
        self.c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.c.fetchone()
    
    def add_balance(self, user_id, amount):
        self.c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()
    
    def claim_bonus(self, user_id):
        today = datetime.now().strftime('%Y-%m-%d')
        user = self.get_user(user_id)
        if user and user[4] != today:
            self.c.execute("UPDATE users SET balance = balance + 100, bonus_claimed = ? WHERE user_id = ?", 
                          (today, user_id))
            self.conn.commit()
            return True, 100
        return False, 0
    
    def add_subscription(self, user_id, bot_type, bot_token, bot_username, bot_name):
        start = datetime.now()
        end = start + timedelta(days=7)
        self.c.execute('''INSERT INTO subscriptions 
                         (user_id, bot_type, bot_token, bot_username, bot_name, start_date, end_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?)''',
                      (user_id, bot_type, bot_token, bot_username, bot_name, start.isoformat(), end.isoformat()))
        self.conn.commit()
        return self.c.lastrowid
    
    def get_user_bots(self, user_id):
        self.c.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active'", (user_id,))
        return self.c.fetchall()
    
    def check_token_exists(self, token):
        self.c.execute("SELECT * FROM subscriptions WHERE bot_token = ?", (token,))
        return self.c.fetchone()
    
    def add_payment(self, user_id, amount, method):
        self.c.execute("INSERT INTO payments (user_id, amount, payment_method, date) VALUES (?, ?, ?, ?)",
                      (user_id, amount, method, datetime.now().isoformat()))
        self.conn.commit()

db = Database()

# ============ BOTLAR KATALOGI ============
BOTS_CATALOG = {
    "weather": {
        "name": "🌤 Ob-havo Boti",
        "desc": "Har qanday shahar ob-havosi\n📍 GPS orqali aniqlash\n📊 7 kunlik prognoz",
        "category": "Ma'lumot",
        "price": 300,
        "icon": "🌤"
    },
    "currency": {
        "name": "💱 Valyuta Konvertori",
        "desc": "150+ valyuta kurslari\n📈 Real-time yangilanish\n📊 Grafik ko'rinish",
        "category": "Moliya",
        "price": 300,
        "icon": "💱"
    },
    "translator": {
        "name": "🌍 Tarjimon Bot",
        "desc": "100+ tilga tarjima\n🎤 Ovozli tarjima\n📸 Rasmdan tarjima",
        "category": "Utility",
        "price": 300,
        "icon": "🌍"
    },
    "todo": {
        "name": "✅ Todo List",
        "desc": "Vazifalar ro'yxati\n⏰ Eslatmalar\n📋 Prioritet belgilash",
        "category": "Produktivlik",
        "price": 300,
        "icon": "✅"
    },
    "qr": {
        "name": "📱 QR Code Generator",
        "desc": "Matn→QR kod\n🎨 Maxsus dizayn\n🖼 Logo qo'shish",
        "category": "Utility",
        "price": 300,
        "icon": "📱"
    },
    "prayer": {
        "name": "🕌 Namoz Vaqtlari",
        "desc": "Aniq namoz vaqtlari\n🧭 Qibla yo'nalishi\n📿 Duo va suralar",
        "category": "Islomiy",
        "price": 300,
        "icon": "🕌"
    },
    "news": {
        "name": "📰 Yangiliklar",
        "desc": "Eng so'nggi yangiliklar\n📡 10+ manba\n🔔 Push notification",
        "category": "Axborot",
        "price": 300,
        "icon": "📰"
    },
    "calculator": {
        "name": "🔢 Kalkulyator",
        "desc": "Matematik amallar\n💱 Valyuta hisobi\n📏 Birlik konvertatsiya",
        "category": "Utility",
        "price": 300,
        "icon": "🔢"
    },
    "reminder": {
        "name": "⏰ Eslatma Boti",
        "desc": "Muhim sanalar\n🔄 Takroriy eslatmalar\n🔊 Ovozli eslatma",
        "category": "Produktivlik",
        "price": 300,
        "icon": "⏰"
    },
    "quiz": {
        "name": "🎮 Viktorina",
        "desc": "Bilim sinovlari\n🏆 Reyting tizimi\n🎁 Mukofotlar",
        "category": "O'yin",
        "price": 300,
        "icon": "🎮"
    },
    "downloader": {
        "name": "📥 Media Yuklovchi",
        "desc": "YouTube video\n📸 Instagram post\n🎵 TikTok video",
        "category": "Utility",
        "price": 300,
        "icon": "📥"
    },
    "stats": {
        "name": "📊 Kanal Statistikasi",
        "desc": "Obunachilar o'sishi\n📈 Post analitikasi\n📄 Hisobotlar",
        "category": "Analitika",
        "price": 300,
        "icon": "📊"
    },
    "moderator": {
        "name": "🛡 Guruh Moderatori",
        "desc": "Spam filtr\n🚫 Avto-ban tizimi\n👋 Xush kelibsiz xabari",
        "category": "Hamjamiyat",
        "price": 300,
        "icon": "🛡"
    },
    "image_editor": {
        "name": "🖼 Rasm Muharriri",
        "desc": "Filtrlar qo'shish\n✍️ Matn yozish\n🎭 Stiker yasash",
        "category": "Dizayn",
        "price": 300,
        "icon": "🖼"
    },
    "random": {
        "name": "🎲 Tasodifiy Generator",
        "desc": "Random sonlar\n🎯 Tanlash g'ildiragi\n🎪 Qur'a tashlash",
        "category": "O'yin",
        "price": 300,
        "icon": "🎲"
    }
}

# ============ INLINE + KEYBOARD MENYU ============
def get_main_keyboard():
    """Asosiy Reply Keyboard"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🛍 KATALOG"), KeyboardButton("📦 BOTLARIM")],
        [KeyboardButton("💰 BALANS"), KeyboardButton("🎁 BONUS")],
        [KeyboardButton("💳 TO'LOV"), KeyboardButton("❓ YORDAM")]
    ], resize_keyboard=True)

def get_inline_main_menu():
    """Inline menyu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("💰 BALANS TO'LDIRISH", callback_data="payment_menu")],
        [InlineKeyboardButton("🎁 KUNLIK BONUS", callback_data="daily_bonus")],
        [InlineKeyboardButton("❓ YORDAM", callback_data="help")]
    ])

# ============ HANDLERLAR ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.full_name)
    
    # Inline menyu
    inline_menu = get_inline_main_menu()
    
    # Reply keyboard
    reply_keyboard = get_main_keyboard()
    
    welcome_text = f"""
🎉 *BOT STORE UZ* ga xush kelibsiz!

👋 Salom, {user.first_name}!

📦 *15 ta professional bot*
✅ *7 kun BEPUL sinov*
💰 *Keyin kuniga atigi 300 so'm*

🎁 *Har kuni 100 so'm bonus!*

⚡️ Tanlang:
    """
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    
    await update.message.reply_text(
        "📋 *Menyu:*",
        reply_markup=inline_menu,
        parse_mode=ParseMode.MARKDOWN
    )

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    # Kategoriyalar bo'yicha
    categories = {}
    for bot_id, bot in BOTS_CATALOG.items():
        cat = bot['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((bot_id, bot))
    
    text = "🎯 *BOTLAR KATALOGI*\n\n"
    keyboard = []
    
    for bot_id, bot in BOTS_CATALOG.items():
        text += f"{bot['icon']} *{bot['name']}*\n"
        text += f"└ {bot['desc'].split(chr(10))[0]}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{bot['icon']} {bot['name']} | 300 so'm/kun",
                callback_data=f"bot_info_{bot_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")])
    
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

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("bot_info_", "")
    bot = BOTS_CATALOG.get(bot_id)
    
    if not bot:
        return
    
    text = f"""
*{bot['icon']} {bot['name']}*

📝 *Tavsif:*
{bot['desc']}

📂 *Kategoriya:* {bot['category']}
🆓 *Bepul muddat:* 7 kun
💰 *Narx:* {bot['price']} so'm/kun

✨ *Nima qilmoqchisiz?*
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL FAOLSHTIRISH", callback_data=f"activate_{bot_id}")],
        [InlineKeyboardButton("💳 SOTIB OLISH", callback_data=f"buy_{bot_id}")],
        [InlineKeyboardButton("◀️ KATALOGGA QAYTISH", callback_data="catalog")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def activate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("activate_", "")
    bot = BOTS_CATALOG.get(bot_id)
    
    context.user_data['activating'] = bot_id
    context.user_data['bot_name'] = bot['name']
    
    text = f"""
🔑 *{bot['name']}* ni faollashtirish

📝 *Qadamba-qadam:*

1️⃣ @BotFather'ga o'ting
2️⃣ /newbot buyrug'ini bering
3️⃣ Bot nomini kiriting (ixtiyoriy)
4️⃣ Username kiriting (oxiri `bot` bilan tugashi kerak)
5️⃣ Olingan TOKENni shu yerga yuboring

⚠️ *Token namunasi:*
`1234567890:AAHdqTcvCHrTabcdefghijklmnopqrs`

🔒 Token xavfsiz saqlanadi!
    """
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ BEKOR QILISH", callback_data="catalog")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Token qabul qilish va tekshirish"""
    if 'activating' not in context.user_data:
        # Oddiy xabar
        await update.message.reply_text(
            "Bot tanlash uchun /start buyrug'ini bering yoki menyudan foydalaning.",
            reply_markup=get_main_keyboard()
        )
        return
    
    user_id = update.message.from_user.id
    token = update.message.text.strip()
    bot_id = context.user_data['activating']
    bot = BOTS_CATALOG.get(bot_id)
    
    # Token formatini tekshirish
    if ':' not in token or len(token) < 45:
        await update.message.reply_text(
            "❌ *Noto'g'ri token formati!*\n\n"
            "Token `1234567890:ABCdef...` ko'rinishida bo'lishi kerak.\n\n"
            "Iltimos @BotFather'dan olingan tokenni to'liq yuboring.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Token mavjudligini tekshirish
    if db.check_token_exists(token):
        await update.message.reply_text(
            "❌ *Bu token allaqachon ro'yxatdan o'tgan!*\n\n"
            "Iltimos @BotFather'dan YANGI bot yarating va yangi token oling.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Tokenni to'g'riligini tekshirish (Telegram API orqali)
    processing_msg = await update.message.reply_text("⏳ Token tekshirilmoqda...")
    
    try:
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        
        # Bazaga saqlash
        sub_id = db.add_subscription(user_id, bot_id, token, bot_info.username, bot['name'])
        
        # Tozalash
        del context.user_data['activating']
        if 'bot_name' in context.user_data:
            del context.user_data['bot_name']
        
        # Admin'ga xabar
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"""
🆕 *YANGI FAOLSHTIRISH*

👤 Foydalanuvchi: {update.message.from_user.full_name}
🆔 ID: `{user_id}`
🤖 Bot: {bot['name']}
🔑 Token: `{token}`
📅 Tugash: {(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')}

Boshqarish: /admin
                """,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await processing_msg.delete()
        
        await update.message.reply_text(
            f"""
✅ *TABRIKLAYMIZ! Bot muvaffaqiyatli faollashtirildi!*

🤖 *Bot:* @{bot_info.username}
📦 *Paket:* {bot['name']}
🆓 *Bepul muddat:* 7 kun
📅 *Tugash sanasi:* {(datetime.now() + timedelta(days=7)).strftime('%d.%m.%Y')}

⚙️ *Endi nima qilish kerak?*
• Botingizga /start yuboring
• Admin sozlamalarni 24 soat ichida to'liq ishga tushiradi

📞 *Yordam kerak bo'lsa:* {ADMIN_USERNAME}
            """,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard()
        )
        
        logger.info(f"✅ Bot faollashtirildi: User={user_id}, Bot={bot_id}, Token={token[:20]}...")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Token tekshirish xatosi: {error_msg}")
        
        await processing_msg.delete()
        
        if "Unauthorized" in error_msg:
            await update.message.reply_text(
                "❌ *Token noto'g'ri yoki eskirgan!*\n\n"
                "Iltimos @BotFather'dan yangi bot yarating va yangi token oling.\n\n"
                "Eslatma: Har safar yangi bot yaratganda yangi token beriladi.",
                parse_mode=ParseMode.MARKDOWN
            )
        elif "Conflict" in error_msg:
            await update.message.reply_text(
                "❌ *Bu token boshqa botda ishlatilgan!*\n\n"
                "Iltimos @BotFather'dan yangi bot yarating.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ *Xatolik yuz berdi!*\n\n"
                f"`{error_msg[:100]}`\n\n"
                f"Iltimos qayta urinib ko'ring yoki {ADMIN_USERNAME} bilan bog'laning.",
                parse_mode=ParseMode.MARKDOWN
            )

async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    bots = db.get_user_bots(user_id)
    
    if not bots:
        text = "📦 *Sizda hali botlar yo'q!*\n\nKatalogdan o'zingizga yoqqan botni tanlang:"
    else:
        text = "📦 *MENING BOTLARIM*\n\n"
        for bot in bots:
            try:
                end_date = datetime.fromisoformat(bot[7])
                days_left = (end_date - datetime.now()).days
                status = "✅" if days_left > 0 else "⚠️"
                text += f"{status} *{bot[5]}*\n"
                text += f"⏳ {max(0, days_left)} kun qoldi\n"
                text += f"🔗 @{bot[4]}\n\n"
            except:
                text += f"✅ *{bot[5]}*\n🔗 @{bot[4]}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🛍 KATALOGGA O'TISH", callback_data="catalog")],
        [InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")]
    ]
    
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

async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    
    success, amount = db.claim_bonus(user_id)
    
    if success:
        text = f"""
🎁 *KUNLIK BONUS*

✅ Tabriklaymiz! Siz {amount} so'm bonus oldingiz!

💰 Joriy balansingizga qo'shildi.

⏰ Keyingi bonus 24 soatdan keyin.
        """
    else:
        text = """
🎁 *KUNLIK BONUS*

❌ Bugun bonusingizni allaqachon olgansiz!

⏰ Ertaga yana keling.
        """
    
    keyboard = [[InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")]]
    
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

async def payment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    user = db.get_user(update.effective_user.id)
    balance = user[3] if user else 0
    
    text = f"""
💳 *TO'LOV TIZIMI*

💰 Joriy balans: {balance} so'm

To'lov usulini tanlang:
    """
    
    keyboard = [
        [InlineKeyboardButton("📱 Click", callback_data="pay_click")],
        [InlineKeyboardButton("💳 Payme", callback_data="pay_payme")],
        [InlineKeyboardButton("💰 Balans to'ldirish", callback_data="top_up")],
        [InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")]
    ]
    
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

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_type = query.data.replace("pay_", "")
    
    text = f"""
💳 *{payment_type.upper()} TO'LOV*

To'lov miqdorini tanlang:
    """
    
    keyboard = [
        [
            InlineKeyboardButton("5 000 so'm", callback_data=f"amount_5000_{payment_type}"),
            InlineKeyboardButton("10 000 so'm", callback_data=f"amount_10000_{payment_type}")
        ],
        [
            InlineKeyboardButton("30 000 so'm", callback_data=f"amount_30000_{payment_type}"),
            InlineKeyboardButton("50 000 so'm", callback_data=f"amount_50000_{payment_type}")
        ],
        [InlineKeyboardButton("◀️ ORQAGA", callback_data="payment_menu")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, amount, method = query.data.split("_")
    amount = int(amount)
    
    # To'lov ma'lumotlari
    payment_info = {
        "click": {
            "name": "Click",
            "number": "+998704785888",
            "instruction": "Click ilovasidan to'lov qiling"
        },
        "payme": {
            "name": "Payme",
            "number": "9860 0825 1273 7923",
            "instruction": "Payme ilovasidan to'lov qiling"
        }
    }
    
    info = payment_info.get(method, {})
    
    text = f"""
💳 *TO'LOV: {amount} so'm*

📱 *{info['name']} orqali:*
• Raqam: `{info['number']}`
• Miqdor: {amount} so'm

📝 *Qadamba-qadam:*
1. {info['instruction']}
2. To'lov chekini shu botga yuboring
3. Admin 24 soat ichida tasdiqlaydi

⚠️ Chek rasm ko'rinishida bo'lishi kerak!
    """
    
    context.user_data['payment_amount'] = amount
    context.user_data['payment_method'] = method
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ ORQAGA", callback_data="payment_menu")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chek rasmini qabul qilish"""
    user_id = update.message.from_user.id
    
    await update.message.reply_text(
        "✅ Chek qabul qilindi!\n\n"
        f"⏰ Admin tez orada tasdiqlaydi.\n"
        f"📞 Shoshilinch bo'lsa: {ADMIN_USERNAME}",
        reply_markup=get_main_keyboard()
    )
    
    # Admin'ga yuborish
    try:
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=user_id,
            message_id=update.message.message_id
        )
        
        await context.bot.send_message(
            ADMIN_ID,
            f"""
💳 *YANGI TO'LOV CHEKI*

👤 User: `{user_id}`
📝 To'lov tasdiqlash kerak!

Tasdiqlash: /confirm {user_id}
            """,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Chek forward error: {e}")

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    
    text = f"""
❓ *YORDAM*

*Ko'p so'raladigan savollar:*

1️⃣ *Bot qanday ishlaydi?*
Katalogdan bot tanlaysiz → Token yuborasiz → Bot ishga tushadi!

2️⃣ *Token nima?*
@BotFather'dan oladigan maxfiy kalit

3️⃣ *To'lov qanday?*
7 kun BEPUL, keyin kuniga 300 so'm

4️⃣ *Bot ishlamasa?*
Admin bilan bog'laning: {ADMIN_USERNAME}

📞 *Qo'shimcha savollar:*
{ADMIN_USERNAME}
    """
    
    keyboard = [[InlineKeyboardButton("◀️ BOSH MENYU", callback_data="main_menu")]]
    
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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnli xabarlarni qayta ishlash"""
    text = update.message.text
    
    if text == "🛍 KATALOG":
        await catalog(update, context)
    elif text == "📦 BOTLARIM":
        await my_bots(update, context)
    elif text == "💰 BALANS":
        user = db.get_user(update.effective_user.id)
        balance = user[3] if user else 0
        await update.message.reply_text(
            f"💰 Sizning balansingiz: {balance} so'm\n\n"
            "Balans to'ldirish uchun: 💳 TO'LOV tugmasini bosing",
            reply_markup=get_main_keyboard()
        )
    elif text == "🎁 BONUS":
        await daily_bonus(update, context)
    elif text == "💳 TO'LOV":
        await payment_menu(update, context)
    elif text == "❓ YORDAM":
        await help_menu(update, context)
    elif 'activating' in context.user_data:
        await receive_token(update, context)
    else:
        await update.message.reply_text(
            "Menyudan foydalaning yoki /start buyrug'ini bering.",
            reply_markup=get_main_keyboard()
        )

def main():
    logger.info("="*50)
    logger.info("🚀 BOT STORE UZ - Professional Versiya")
    logger.info(f"Admin: {ADMIN_USERNAME}")
    logger.info("="*50)
    
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    
    # Callback handlerlar
    app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(bot_info, pattern="^bot_info_"))
    app.add_handler(CallbackQueryHandler(activate_bot, pattern="^activate_"))
    app.add_handler(CallbackQueryHandler(my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(daily_bonus, pattern="^daily_bonus$"))
    app.add_handler(CallbackQueryHandler(payment_menu, pattern="^payment_menu$"))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(process_amount, pattern="^amount_"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    
    # Message handlerlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Barcha handlerlar yuklandi")
    logger.info("🎯 Bot ishga tushdi!")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
