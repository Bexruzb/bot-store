import sys
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

TOKEN = sys.argv[1] if len(sys.argv) > 1 else "TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

# Database
import sqlite3
conn = sqlite3.connect(f'shop_{ADMIN_ID}.db', check_same_thread=False)
c = conn.cursor()
c.executescript('''
    CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, description TEXT, photo TEXT);
    CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, quantity INTEGER, status TEXT, date TEXT);
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
''')
conn.commit()

# Sozlamalar
c.execute("INSERT OR IGNORE INTO settings VALUES ('shop_name', 'Mening Do\'konim')")
c.execute("INSERT OR IGNORE INTO settings VALUES ('currency', 'so\'m')")
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📦 Mahsulotlar", callback_data="products")],
            [InlineKeyboardButton("➕ Mahsulot qo'shish", callback_data="add_product")],
            [InlineKeyboardButton("📊 Buyurtmalar", callback_data="orders")],
            [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="settings")],
            [InlineKeyboardButton("📢 Do'konga o'tish", callback_data="shop_view")]
        ]
        text = f"👑 *ADMIN PANEL*\n\nDo'koningizga xush kelibsiz!"
    else:
        keyboard = [
            [InlineKeyboardButton("🛍 Mahsulotlarni ko'rish", callback_data="shop_view")],
            [InlineKeyboardButton("🛒 Savatcha", callback_data="cart")],
            [InlineKeyboardButton("📞 Aloqa", callback_data="contact")]
        ]
        text = f"🛍 *{get_setting('shop_name')}* ga xush kelibsiz!\n\nMahsulotlarni ko'ring:"
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

def get_setting(key):
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    result = c.fetchone()
    return result[0] if result else ""

async def shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    
    if not products:
        text = "📦 Hozircha mahsulotlar yo'q!"
        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data="start")]]
    else:
        text = f"🛍 *{get_setting('shop_name')}*\n\nMahsulotlar:"
        keyboard = []
        for p in products:
            keyboard.append([
                InlineKeyboardButton(f"{p[1]} - {p[2]:,} so'm", callback_data=f"product_{p[0]}")
            ])
        keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="start")])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# Qolgan handlerlar...
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "start":
        await start(update, context)
    elif query.data == "shop_view":
        await shop_view(update, context)
    else:
        await query.edit_message_text("⚙️ Bu funksiya hozir ishlab chiqilmoqda...")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"🛍 Do'kon boti ishga tushdi! Admin: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
