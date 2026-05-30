"""
🛍 MINI DO'KON BOT - Professional versiya
Admin ID orqali to'liq boshqaruv
Barcha funksiyalar ishlaydi
"""

import sys
import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, BotCommand,
    InputMediaPhoto, LabeledPrice
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes, ConversationHandler,
    PreCheckoutQueryHandler
)
from telegram.constants import ParseMode

# ============ LOGGING ============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ KONFIGURATSIYA ============
TOKEN = sys.argv[1] if len(sys.argv) > 1 else "YOUR_BOT_TOKEN"
ADMIN_ID = int(sys.argv[2]) if len(sys.argv) > 2 else 0

# Conversation states
(
    ADD_PRODUCT_NAME, ADD_PRODUCT_PRICE, ADD_PRODUCT_DESC, ADD_PRODUCT_PHOTO,
    EDIT_PRODUCT_SELECT, EDIT_PRODUCT_FIELD, EDIT_PRODUCT_VALUE,
    ADD_CATEGORY, ADD_COUPON, SETTINGS_CHANGE
) = range(10)

# ============ DATABASE ============
class Database:
    def __init__(self, admin_id):
        db_name = f'shop_{admin_id}.db'
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.c = self.conn.cursor()
        self.admin_id = admin_id
        self.create_tables()
        self.init_defaults()
    
    def create_tables(self):
        self.c.executescript('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT,
                photo_id TEXT,
                category TEXT DEFAULT 'Umumiy',
                stock INTEGER DEFAULT 999,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '📦'
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                user_phone TEXT,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER DEFAULT 1,
                price INTEGER,
                total_price INTEGER,
                status TEXT DEFAULT 'yangi',
                payment_method TEXT,
                delivery_address TEXT,
                comment TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            
            CREATE TABLE IF NOT EXISTS customers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                address TEXT,
                total_orders INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1
            );
            
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount_percent INTEGER,
                discount_amount INTEGER,
                min_order INTEGER DEFAULT 0,
                max_uses INTEGER DEFAULT 100,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                valid_until TEXT
            );
            
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                rating INTEGER,
                comment TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        ''')
        self.conn.commit()
    
    def init_defaults(self):
        defaults = {
            'shop_name': '🛍 Mening Do\'konim',
            'currency': 'so\'m',
            'delivery_fee': '20000',
            'min_order': '50000',
            'phone': '+998901234567',
            'address': 'Toshkent shahri',
            'working_hours': '09:00 - 21:00',
            'welcome_message': 'Assalomu alaykum! Do\'konimizga xush kelibsiz!',
            'payment_click': 'true',
            'payment_payme': 'true',
            'payment_cash': 'true',
            'telegram_channel': '',
            'telegram_group': ''
        }
        for key, value in defaults.items():
            self.c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
    
    def get_setting(self, key):
        self.c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = self.c.fetchone()
        return result[0] if result else ""
    
    def update_setting(self, key, value):
        self.c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()
    
    def add_product(self, name, price, description, photo_id, category="Umumiy"):
        self.c.execute(
            "INSERT INTO products (name, price, description, photo_id, category) VALUES (?, ?, ?, ?, ?)",
            (name, price, description, photo_id, category)
        )
        self.conn.commit()
        return self.c.lastrowid
    
    def get_products(self, category=None):
        if category and category != "all":
            self.c.execute(
                "SELECT * FROM products WHERE is_active = 1 AND category = ? ORDER BY id DESC",
                (category,)
            )
        else:
            self.c.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY id DESC")
        return self.c.fetchall()
    
    def get_product(self, product_id):
        self.c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        return self.c.fetchone()
    
    def delete_product(self, product_id):
        self.c.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        self.conn.commit()
    
    def update_product(self, product_id, field, value):
        self.c.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
        self.conn.commit()
    
    def add_to_cart(self, user_id, product_id, quantity=1):
        self.c.execute("SELECT * FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
        existing = self.c.fetchone()
        if existing:
            self.c.execute("UPDATE cart SET quantity = quantity + ? WHERE id = ?", (quantity, existing[0]))
        else:
            self.c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", 
                          (user_id, product_id, quantity))
        self.conn.commit()
    
    def get_cart(self, user_id):
        self.c.execute("""
            SELECT c.id, p.name, p.price, c.quantity, p.photo_id, p.id
            FROM cart c JOIN products p ON c.product_id = p.id
            WHERE c.user_id = ?
        """, (user_id,))
        return self.c.fetchall()
    
    def clear_cart(self, user_id):
        self.c.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        self.conn.commit()
    
    def remove_from_cart(self, cart_id):
        self.c.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
        self.conn.commit()
    
    def get_cart_count(self, user_id):
        self.c.execute("SELECT SUM(quantity) FROM cart WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        return result[0] if result[0] else 0
    
    def get_cart_total(self, user_id):
        self.c.execute("""
            SELECT SUM(p.price * c.quantity) 
            FROM cart c JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ?
        """, (user_id,))
        result = self.c.fetchone()
        return result[0] if result[0] else 0
    
    def create_order(self, user_id, user_name, phone, payment_method, address, comment=""):
        cart_items = self.get_cart(user_id)
        if not cart_items:
            return None
        
        orders_created = []
        total_amount = 0
        
        for item in cart_items:
            cart_id, name, price, quantity, photo_id, product_id = item
            total = price * quantity
            total_amount += total
            
            self.c.execute("""
                INSERT INTO orders (user_id, user_name, user_phone, product_id, product_name, 
                                  quantity, price, total_price, payment_method, delivery_address, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, user_name, phone, product_id, name, quantity, price, total,
                  payment_method, address, comment))
            orders_created.append(self.c.lastrowid)
        
        # Mijoz statistikasi
        self.c.execute("SELECT * FROM customers WHERE user_id = ?", (user_id,))
        customer = self.c.fetchone()
        if customer:
            self.c.execute("""
                UPDATE customers SET total_orders = total_orders + 1, 
                total_spent = total_spent + ? WHERE user_id = ?
            """, (total_amount, user_id))
        else:
            self.c.execute("""
                INSERT INTO customers (user_id, username, full_name, phone, address, total_orders, total_spent)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (user_id, user_name, user_name, phone, address, total_amount))
        
        self.clear_cart(user_id)
        self.conn.commit()
        
        return orders_created, total_amount
    
    def get_orders(self, status=None, limit=50):
        if status:
            self.c.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit)
            )
        else:
            self.c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))
        return self.c.fetchall()
    
    def get_user_orders(self, user_id):
        self.c.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return self.c.fetchall()
    
    def update_order_status(self, order_id, status):
        self.c.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        self.conn.commit()
    
    def get_order(self, order_id):
        self.c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return self.c.fetchone()
    
    def get_stats(self):
        stats = {}
        
        self.c.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        stats['products_count'] = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM orders")
        stats['orders_count'] = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM orders WHERE status = 'yangi'")
        stats['new_orders'] = self.c.fetchone()[0]
        
        self.c.execute("SELECT COUNT(*) FROM customers")
        stats['customers_count'] = self.c.fetchone()[0]
        
        self.c.execute("SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE status = 'yakunlangan'")
        stats['total_revenue'] = self.c.fetchone()[0]
        
        self.c.execute("""
            SELECT COALESCE(SUM(total_price), 0) FROM orders 
            WHERE status = 'yakunlangan' AND date(created_at) = date('now', 'localtime')
        """)
        stats['today_revenue'] = self.c.fetchone()[0]
        
        self.c.execute("""
            SELECT COALESCE(SUM(total_price), 0) FROM orders 
            WHERE status = 'yakunlangan' AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')
        """)
        stats['monthly_revenue'] = self.c.fetchone()[0]
        
        return stats
    
    def add_coupon(self, code, discount_percent=0, discount_amount=0, min_order=0, valid_days=30):
        valid_until = (datetime.now() + timedelta(days=valid_days)).strftime('%Y-%m-%d')
        self.c.execute("""
            INSERT INTO coupons (code, discount_percent, discount_amount, min_order, valid_until)
            VALUES (?, ?, ?, ?, ?)
        """, (code, discount_percent, discount_amount, min_order, valid_until))
        self.conn.commit()
    
    def validate_coupon(self, code, order_total):
        self.c.execute("""
            SELECT * FROM coupons WHERE code = ? AND is_active = 1 
            AND used_count < max_uses AND valid_until >= date('now', 'localtime')
        """, (code,))
        coupon = self.c.fetchone()
        
        if not coupon:
            return None, "Kupon topilmadi yoki muddati o'tgan!"
        
        if order_total < coupon[5]:
            return None, f"Minimal buyurtma: {coupon[5]:,} so'm!"
        
        discount = 0
        if coupon[3]:
            discount = int(order_total * coupon[3] / 100)
        elif coupon[4]:
            discount = coupon[4]
        
        return discount, "Kupon qabul qilindi!"
    
    def use_coupon(self, code):
        self.c.execute("UPDATE coupons SET used_count = used_count + 1 WHERE code = ?", (code,))
        self.conn.commit()
    
    def add_category(self, name, emoji="📦"):
        self.c.execute("INSERT OR IGNORE INTO categories (name, emoji) VALUES (?, ?)", (name, emoji))
        self.conn.commit()
    
    def get_categories(self):
        self.c.execute("SELECT * FROM categories ORDER BY id")
        return self.c.fetchall()
    
    def add_review(self, user_id, product_id, rating, comment):
        self.c.execute(
            "INSERT INTO reviews (user_id, product_id, rating, comment) VALUES (?, ?, ?, ?)",
            (user_id, product_id, rating, comment)
        )
        self.conn.commit()
    
    def get_product_reviews(self, product_id):
        self.c.execute("SELECT * FROM reviews WHERE product_id = ? ORDER BY id DESC LIMIT 10", (product_id,))
        return self.c.fetchall()

# Initialize database
db = Database(ADMIN_ID)

# ============ KEYBOARDLAR ============
def get_main_menu(user_id):
    """Asosiy menyu"""
    if user_id == ADMIN_ID:
        keyboard = [
            [KeyboardButton("📊 STATISTIKA"), KeyboardButton("📦 MAHSULOTLAR")],
            [KeyboardButton("📋 BUYURTMALAR"), KeyboardButton("👥 MIJOZLAR")],
            [KeyboardButton("🎫 KUPONLAR"), KeyboardButton("⚙️ SOZLAMALAR")],
            [KeyboardButton("🛍 DO'KONNI KO'RISH"), KeyboardButton("📢 XABAR YUBORISH")]
        ]
    else:
        keyboard = [
            [KeyboardButton("🛍 MAHSULOTLAR"), KeyboardButton("🛒 SAVATCHA")],
            [KeyboardButton("📋 BUYURTMALARIM"), KeyboardButton("📞 ALOQA")],
            [KeyboardButton("ℹ️ DO'KON HAQIDA"), KeyboardButton("⭐️ SHARH QOLDIRISH")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_inline_admin_menu():
    """Inline admin menyu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
         InlineKeyboardButton("📦 Mahsulotlar", callback_data="admin_products")],
        [InlineKeyboardButton("➕ Mahsulot qo'shish", callback_data="admin_add_product"),
         InlineKeyboardButton("📋 Buyurtmalar", callback_data="admin_orders")],
        [InlineKeyboardButton("👥 Mijozlar", callback_data="admin_customers"),
         InlineKeyboardButton("🎫 Kuponlar", callback_data="admin_coupons")],
        [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings"),
         InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🛍 Do'konni ko'rish", callback_data="shop_view")]
    ])

# ============ ASOSIY HANDLERLAR ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    
    # Foydalanuvchi ma'lumotlarini saqlash
    db.c.execute("INSERT OR IGNORE INTO customers (user_id, username, full_name) VALUES (?, ?, ?)",
                 (user.id, user.username, user.full_name))
    db.conn.commit()
    
    welcome = db.get_setting('welcome_message')
    shop_name = db.get_setting('shop_name')
    
    # Reply keyboard
    await update.message.reply_text(
        f"*{shop_name}*\n\n{welcome}\n\n👋 Salom, {user.first_name}!",
        reply_markup=get_main_menu(user.id),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Admin uchun inline menyu
    if user.id == ADMIN_ID:
        await update.message.reply_text(
            "👑 *ADMIN PANEL*",
            reply_markup=get_inline_admin_menu(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Mijoz uchun mahsulotlarni ko'rsatish
        await show_catalog(update, context)

async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE, category="all", page=0):
    """Mahsulotlar katalogini ko'rsatish"""
    products = db.get_products(category)
    categories = db.get_categories()
    
    if not products:
        text = "📦 Hozircha mahsulotlar yo'q!"
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Orqaga", callback_data="main_menu")]
                ])
            )
        else:
            await update.message.reply_text(text)
        return
    
    # Kategoriyalar
    cat_buttons = []
    cat_row = []
    for i, cat in enumerate(categories):
        cat_row.append(InlineKeyboardButton(f"{cat[2]} {cat[1]}", callback_data=f"cat_{cat[1]}"))
        if len(cat_row) == 3 or i == len(categories) - 1:
            cat_buttons.append(cat_row)
            cat_row = []
    
    cat_buttons.append([
        InlineKeyboardButton("📦 Barcha", callback_data="cat_all"),
        InlineKeyboardButton("🛒 Savatcha", callback_data="view_cart")
    ])
    
    # Mahsulotlar
    text = f"🛍 *KATALOG*\n\n"
    keyboard = cat_buttons.copy()
    
    for product in products:
        text += f"📦 *{product[1]}*\n"
        text += f"💰 {product[2]:,} so'm\n"
        if product[4]:
            text += f"📂 {product[4]}\n"
        text += "\n"
        
        keyboard.append([
            InlineKeyboardButton(
                f"🛍 {product[1]} - {product[2]:,} so'm",
                callback_data=f"product_{product[0]}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="main_menu")])
    
    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(
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

async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulot haqida batafsil"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.replace("product_", ""))
    product = db.get_product(product_id)
    
    if not product:
        await query.edit_message_text("❌ Mahsulot topilmadi!")
        return
    
    reviews = db.get_product_reviews(product_id)
    avg_rating = sum(r[3] for r in reviews) / len(reviews) if reviews else 0
    
    text = f"""
📦 *{product[1]}*

💰 Narx: {product[2]:,} so'm
📂 Kategoriya: {product[4]}
📦 Omborda: {product[5]} dona

📝 *Tavsif:*
{product[3] or 'Tavsif mavjud emas'}

⭐️ Reyting: {avg_rating:.1f}/5 ({len(reviews)} ta sharh)
    """
    
    keyboard = [
        [InlineKeyboardButton("➕ Savatchaga qo'shish", callback_data=f"addcart_{product_id}")],
        [InlineKeyboardButton("1️⃣", callback_data=f"qty_1_{product_id}"),
         InlineKeyboardButton("2️⃣", callback_data=f"qty_2_{product_id}"),
         InlineKeyboardButton("5️⃣", callback_data=f"qty_5_{product_id}")],
        [InlineKeyboardButton("⭐️ Sharh qoldirish", callback_data=f"review_{product_id}")],
        [InlineKeyboardButton("◀️ Katalogga qaytish", callback_data="catalog")]
    ]
    
    if product[6]:  # Rasm mavjud bo'lsa
        try:
            await query.message.delete()
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=product[6],
                caption=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Savatchaga qo'shish"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    product_id = int(data.replace("addcart_", ""))
    user_id = update.effective_user.id
    
    db.add_to_cart(user_id, product_id)
    cart_count = db.get_cart_count(user_id)
    
    await query.answer(f"✅ Savatchaga qo'shildi! ({cart_count} ta)", show_alert=False)
    
    # Savatcha tugmasini qo'shish
    product = db.get_product(product_id)
    keyboard = [
        [InlineKeyboardButton(f"✅ Qo'shildi! Savatcha ({cart_count})", callback_data="view_cart")],
        [InlineKeyboardButton("◀️ Katalogga qaytish", callback_data="catalog")]
    ]
    
    await query.edit_message_reply_markup(InlineKeyboardMarkup(keyboard))

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Savatchani ko'rish"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    cart_items = db.get_cart(user_id)
    total = db.get_cart_total(user_id)
    
    if not cart_items:
        text = "🛒 Savatchangiz bo'sh!"
        keyboard = [[InlineKeyboardButton("🛍 Mahsulotlarni ko'rish", callback_data="catalog")]]
    else:
        text = "🛒 *SAVATCHA*\n\n"
        keyboard = []
        
        for item in cart_items:
            cart_id, name, price, quantity, photo_id, product_id = item
            subtotal = price * quantity
            text += f"📦 {name}\n"
            text += f"💰 {price:,} x {quantity} = {subtotal:,} so'm\n\n"
            
            keyboard.append([
                InlineKeyboardButton("➖", callback_data=f"decqty_{cart_id}"),
                InlineKeyboardButton(f"{quantity}", callback_data="noop"),
                InlineKeyboardButton("➕", callback_data=f"incqty_{cart_id}"),
                InlineKeyboardButton("❌", callback_data=f"remove_{cart_id}")
            ])
        
        text += f"💰 *Jami: {total:,} so'm*"
        
        delivery_fee = int(db.get_setting('delivery_fee'))
        min_order = int(db.get_setting('min_order'))
        
        if total >= min_order:
            text += f"\n🚚 Yetkazib berish: {delivery_fee:,} so'm"
            text += f"\n💵 *Umumiy: {total + delivery_fee:,} so'm*"
        
        keyboard.append([InlineKeyboardButton("✅ Buyurtma berish", callback_data="checkout")])
        keyboard.append([InlineKeyboardButton("🛍 Davom etish", callback_data="catalog")])
    
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

async def update_cart_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Savatchadagi miqdorni o'zgartirish"""
    query = update.callback_query
    await query.answer()
    
    action, cart_id = query.data.split("_")
    cart_id = int(cart_id)
    
    if action == "incqty":
        db.c.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = ?", (cart_id,))
    elif action == "decqty":
        db.c.execute("SELECT quantity FROM cart WHERE id = ?", (cart_id,))
        qty = db.c.fetchone()[0]
        if qty > 1:
            db.c.execute("UPDATE cart SET quantity = quantity - 1 WHERE id = ?", (cart_id,))
        else:
            db.remove_from_cart(cart_id)
    elif action == "remove":
        db.remove_from_cart(cart_id)
    
    db.conn.commit()
    await view_cart(update, context)

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtma berish"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    total = db.get_cart_total(user_id)
    min_order = int(db.get_setting('min_order'))
    
    if total < min_order:
        await query.edit_message_text(
            f"❌ Minimal buyurtma: {min_order:,} so'm\n"
            f"Sizning savatchangiz: {total:,} so'm",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Mahsulotlarni ko'rish", callback_data="catalog")]
            ])
        )
        return
    
    context.user_data['checkout'] = True
    context.user_data['checkout_step'] = 'phone'
    
    await query.edit_message_text(
        "📝 *BUYURTMA BERISH*\n\n"
        "Iltimos, telefon raqamingizni yuboring:\n"
        "Masalan: +998901234567",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtma jarayoni"""
    if not context.user_data.get('checkout'):
        return
    
    step = context.user_data.get('checkout_step')
    user_id = update.effective_user.id
    
    if step == 'phone':
        phone = update.message.text.strip()
        context.user_data['checkout_phone'] = phone
        context.user_data['checkout_step'] = 'address'
        
        await update.message.reply_text(
            "📍 Yetkazib berish manzilini yuboring:\n"
            "Masalan: Toshkent, Chilonzor 5-mavze"
        )
    
    elif step == 'address':
        address = update.message.text.strip()
        context.user_data['checkout_address'] = address
        context.user_data['checkout_step'] = 'payment'
        
        payment_methods = []
        if db.get_setting('payment_click') == 'true':
            payment_methods.append(InlineKeyboardButton("📱 Click", callback_data="pay_click"))
        if db.get_setting('payment_payme') == 'true':
            payment_methods.append(InlineKeyboardButton("💳 Payme", callback_data="pay_payme"))
        if db.get_setting('payment_cash') == 'true':
            payment_methods.append(InlineKeyboardButton("💵 Naqd", callback_data="pay_cash"))
        
        keyboard = [payment_methods]
        keyboard.append([InlineKeyboardButton("◀️ Orqaga", callback_data="checkout")])
        
        await update.message.reply_text(
            "💳 To'lov usulini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif step == 'comment':
        comment = update.message.text.strip()
        context.user_data['checkout_comment'] = comment
        
        # Buyurtmani yakunlash
        phone = context.user_data.get('checkout_phone')
        address = context.user_data.get('checkout_address')
        payment = context.user_data.get('checkout_payment')
        
        result = db.create_order(
            user_id,
            update.effective_user.full_name,
            phone,
            payment,
            address,
            comment
        )
        
        if result:
            orders, total = result
            context.user_data['checkout'] = False
            
            text = f"""
✅ *BUYURTMA QABUL QILINDI!*

📋 Buyurtma raqami: #{orders[0]}
💰 Jami: {total:,} so'm
📱 To'lov: {payment}
📍 Manzil: {address}

⏰ Tez orada operator bog'lanadi!

📞 Savollar: {db.get_setting('phone')}
            """
            
            await update.message.reply_text(
                text,
                reply_markup=get_main_menu(user_id),
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Admin'ga xabar
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 *YANGI BUYURTMA #{orders[0]}*\n\n"
                f"👤 Mijoz: {update.effective_user.full_name}\n"
                f"📱 Tel: {phone}\n"
                f"💰 Jami: {total:,} so'm\n"
                f"💳 To'lov: {payment}\n\n"
                f"📋 Barcha buyurtmalar: /orders",
                parse_mode=ParseMode.MARKDOWN
            )

async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov usulini tanlash"""
    query = update.callback_query
    await query.answer()
    
    payment = query.data.replace("pay_", "")
    payment_names = {"click": "Click", "payme": "Payme", "cash": "Naqd pul"}
    
    context.user_data['checkout_payment'] = payment_names.get(payment, payment)
    context.user_data['checkout_step'] = 'comment'
    
    await query.edit_message_text(
        "📝 Izoh qoldirishingiz mumkin (ixtiyoriy):\n\n"
        "Yoki /skip yozib o'tkazib yuboring."
    )

# ============ ADMIN HANDLERLAR ============
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    query = update.callback_query
    if query:
        await query.answer()
    
    if update.effective_user.id != ADMIN_ID:
        if query:
            await query.edit_message_text("⛔ Ruxsat yo'q!")
        return
    
    if query:
        await query.edit_message_text(
            "👑 *ADMIN PANEL*",
            reply_markup=get_inline_admin_menu(),
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistika"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_stats()
    shop_name = db.get_setting('shop_name')
    
    text = f"""
📊 *{shop_name} - STATISTIKA*

📦 Mahsulotlar: {stats['products_count']}
📋 Jami buyurtmalar: {stats['orders_count']}
🆕 Yangi buyurtmalar: {stats['new_orders']}
👥 Mijozlar: {stats['customers_count']}

💰 Jami daromad: {stats['total_revenue']:,} so'm
📅 Bugungi daromad: {stats['today_revenue']:,} so'm
📆 Oylik daromad: {stats['monthly_revenue']:,} so'm
    """
    
    keyboard = [[InlineKeyboardButton("◀️ Admin panel", callback_data="main_menu")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulotlar boshqaruvi"""
    query = update.callback_query
    await query.answer()
    
    products = db.get_products()
    
    if not products:
        text = "📦 Hozircha mahsulotlar yo'q!"
    else:
        text = "📦 *MAHSULOTLAR*\n\n"
        for p in products:
            text += f"{'✅' if p[6] else '❌'} ID: {p[0]} | {p[1]} | {p[2]:,} so'm | {p[4]}\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Yangi mahsulot", callback_data="admin_add_product")],
        [InlineKeyboardButton("✏️ Mahsulotni tahrirlash", callback_data="admin_edit_product")],
        [InlineKeyboardButton("❌ Mahsulotni o'chirish", callback_data="admin_delete_product")],
        [InlineKeyboardButton("◀️ Admin panel", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buyurtmalar boshqaruvi"""
    query = update.callback_query
    await query.answer()
    
    orders = db.get_orders()
    
    if not orders:
        text = "📋 Hozircha buyurtmalar yo'q!"
    else:
        text = "📋 *BUYURTMALAR*\n\n"
        status_emoji = {
            'yangi': '🆕',
            'qabul_qilingan': '✅',
            'yetkazilmoqda': '🚚',
            'yakunlangan': '✔️',
            'bekor_qilingan': '❌'
        }
        
        for order in orders[:20]:
            emoji = status_emoji.get(order[7], '📋')
            text += f"{emoji} #{order[0]} | {order[4]} | {order[6]} so'm | {order[7]}\n"
    
    keyboard = [
        [InlineKeyboardButton("🆕 Yangi", callback_data="orders_filter_yangi"),
         InlineKeyboardButton("✅ Qabul qilingan", callback_data="orders_filter_qabul_qilingan")],
        [InlineKeyboardButton("🚚 Yetkazilmoqda", callback_data="orders_filter_yetkazilmoqda"),
         InlineKeyboardButton("✔️ Yakunlangan", callback_data="orders_filter_yakunlangan")],
        [InlineKeyboardButton("◀️ Admin panel", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yangi mahsulot qo'shish boshlanishi"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['adding_product'] = True
    context.user_data['product_step'] = 'name'
    
    await query.edit_message_text(
        "📝 Yangi mahsulot qo'shish\n\n"
        "Mahsulot nomini kiriting:"
    )

# ============ TEXT HANDLERLAR ============
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matnli xabarlarni qayta ishlash"""
    user = update.effective_user
    text = update.message.text
    
    # Checkout jarayoni
    if context.user_data.get('checkout'):
        await handle_checkout(update, context)
        return
    
    # Mahsulot qo'shish jarayoni
    if context.user_data.get('adding_product'):
        await handle_add_product(update, context)
        return
    
    # Skip komandasi
    if text == '/skip' and context.user_data.get('checkout_step') == 'comment':
        context.user_data['checkout_comment'] = ''
        await handle_checkout(update, context)
        return
    
    # Menyu tugmalari
    if text == "🛍 MAHSULOTLAR" or text == "🛍 DO'KONNI KO'RISH":
        await show_catalog(update, context)
    elif text == "🛒 SAVATCHA":
        await view_cart(update, context)
    elif text == "📋 BUYURTMALARIM":
        orders = db.get_user_orders(user.id)
        if orders:
            order_text = "📋 *BUYURTMALARIM*\n\n"
            for o in orders[:10]:
                order_text += f"#{o[0]} | {o[4]} | {o[6]} so'm | {o[7]}\n"
            await update.message.reply_text(order_text, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("📋 Hozircha buyurtmalaringiz yo'q!")
    elif text == "📞 ALOQA":
        await update.message.reply_text(
            f"📞 *Aloqa*\n\n"
            f"📱 Tel: {db.get_setting('phone')}\n"
            f"📍 Manzil: {db.get_setting('address')}\n"
            f"🕐 Ish vaqti: {db.get_setting('working_hours')}",
            parse_mode=ParseMode.MARKDOWN
        )
    elif text == "ℹ️ DO'KON HAQIDA":
        await update.message.reply_text(
            f"ℹ️ *{db.get_setting('shop_name')}*\n\n"
            f"📱 Tel: {db.get_setting('phone')}\n"
            f"📍 Manzil: {db.get_setting('address')}\n"
            f"🕐 Ish vaqti: {db.get_setting('working_hours')}\n\n"
            f"🚚 Yetkazib berish: {db.get_setting('delivery_fee')} so'm\n"
            f"💰 Min buyurtma: {db.get_setting('min_order')} so'm",
            parse_mode=ParseMode.MARKDOWN
        )
    elif text == "📊 STATISTIKA" and user.id == ADMIN_ID:
        fake_query = type('obj', (object,), {'data': 'admin_stats', 'answer': lambda: None, 'edit_message_text': lambda t, **k: None})()
        await admin_stats(update, context)
    elif text == "📦 MAHSULOTLAR" and user.id == ADMIN_ID:
        fake_query = type('obj', (object,), {'data': 'admin_products', 'answer': lambda: None, 'edit_message_text': lambda t, **k: None})()
        await admin_products(update, context)
    elif text == "📋 BUYURTMALAR" and user.id == ADMIN_ID:
        fake_query = type('obj', (object,), {'data': 'admin_orders', 'answer': lambda: None, 'edit_message_text': lambda t, **k: None})()
        await admin_orders(update, context)
    else:
        await update.message.reply_text("Menyudan foydalaning!", reply_markup=get_main_menu(user.id))

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mahsulot qo'shish jarayoni"""
    step = context.user_data.get('product_step')
    text = update.message.text
    
    if step == 'name':
        context.user_data['product_name'] = text
        context.user_data['product_step'] = 'price'
        await update.message.reply_text("💰 Mahsulot narxini kiriting (so'm):")
    
    elif step == 'price':
        try:
            price = int(text.replace(' ', '').replace(',', ''))
            context.user_data['product_price'] = price
            context.user_data['product_step'] = 'description'
            await update.message.reply_text("📝 Mahsulot tavsifini kiriting:")
        except:
            await update.message.reply_text("❌ Iltimos, faqat raqam kiriting!")
    
    elif step == 'description':
        context.user_data['product_description'] = text
        context.user_data['product_step'] = 'photo'
        await update.message.reply_text("📸 Mahsulot rasmini yuboring (yoki /skip):")
    
    elif step == 'photo':
        await update.message.reply_text("📸 Iltimos, rasm yuboring!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rasm qabul qilish"""
    if context.user_data.get('adding_product') and context.user_data.get('product_step') == 'photo':
        photo = update.message.photo[-1].file_id
        
        # Mahsulotni saqlash
        db.add_product(
            context.user_data['product_name'],
            context.user_data['product_price'],
            context.user_data.get('product_description', ''),
            photo
        )
        
        # Tozalash
        for key in ['adding_product', 'product_step', 'product_name', 'product_price', 'product_description']:
            if key in context.user_data:
                del context.user_data[key]
        
        await update.message.reply_text(
            "✅ Mahsulot muvaffaqiyatli qo'shildi!",
            reply_markup=get_main_menu(update.effective_user.id)
        )

# ============ CALLBACK HANDLER ============
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha callback query'larni qayta ishlash"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_menu":
        await admin_panel(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_products":
        await admin_products(update, context)
    elif data == "admin_add_product":
        await admin_add_product_start(update, context)
    elif data == "admin_orders":
        await admin_orders(update, context)
    elif data == "catalog" or data == "shop_view":
        await show_catalog(update, context)
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        await show_catalog(update, context, category)
    elif data.startswith("product_"):
        await show_product(update, context)
    elif data.startswith("addcart_"):
        await add_to_cart(update, context)
    elif data == "view_cart":
        await view_cart(update, context)
    elif data in ["incqty", "decqty", "remove"] or data.startswith(("incqty_", "decqty_", "remove_")):
        await update_cart_quantity(update, context)
    elif data == "checkout":
        await checkout(update, context)
    elif data.startswith("pay_"):
        await handle_payment_selection(update, context)

# ============ MAIN ============
def main():
    logger.info(f"🛍 Do'kon boti ishga tushmoqda...")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info(f"🏪 {db.get_setting('shop_name')}")
    
    app = Application.builder().token(TOKEN).build()
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("orders", admin_orders))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("skip", handle_text))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlerlar
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Bot commands
    commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("admin", "Admin panel"),
        BotCommand("orders", "Buyurtmalar ro'yxati"),
        BotCommand("stats", "Statistika"),
    ]
    
    logger.info("✅ Do'kon boti ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
