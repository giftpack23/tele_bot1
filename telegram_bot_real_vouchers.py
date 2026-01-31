"""
Advanced Telegram Bot with REAL Voucher Management System
- Channel verification
- Referral system (1 referral = 1 point)
- Real Shein voucher codes distribution
- Admin panel for adding vouchers
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import json
import os
from datetime import datetime

# ⚠️ CONFIGURED VALUES
BOT_TOKEN = "8105173539:AAFgcUDueRvibS5ieuXH8T913Y1i4Hbxnew"
CHANNEL_ID = -1003605508755
CHANNEL_LINK = "https://t.me/+97wLvWe17YU0NmI1"

# ⚠️ ADMIN USER ID - Replace with YOUR Telegram user ID
# Apni ID pata karne ke liye: @userinfobot ko message karein
ADMIN_USER_ID = 123456789  # CHANGE THIS TO YOUR USER ID

# Database files
DATABASE_FILE = "users_database.json"
VOUCHERS_STOCK_FILE = "vouchers_stock.json"
VOUCHERS_CLAIMED_FILE = "vouchers_claimed.json"

# Voucher prices
VOUCHER_PRICES = {
    "500": 2,
    "1000": 4,
    "2000": 7
}


def load_database():
    """User database load karo"""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_database(data):
    """User database save karo"""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_vouchers_stock():
    """Available vouchers load karo"""
    if os.path.exists(VOUCHERS_STOCK_FILE):
        with open(VOUCHERS_STOCK_FILE, 'r') as f:
            return json.load(f)
    return {"500": [], "1000": [], "2000": []}


def save_vouchers_stock(data):
    """Vouchers stock save karo"""
    with open(VOUCHERS_STOCK_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_claimed_vouchers():
    """Claimed vouchers history load karo"""
    if os.path.exists(VOUCHERS_CLAIMED_FILE):
        with open(VOUCHERS_CLAIMED_FILE, 'r') as f:
            return json.load(f)
    return []


def save_claimed_vouchers(data):
    """Claimed vouchers save karo"""
    with open(VOUCHERS_CLAIMED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_voucher_to_stock(amount, code):
    """Stock mein voucher add karo"""
    stock = load_vouchers_stock()
    if amount in stock:
        if code not in stock[amount]:
            stock[amount].append(code)
            save_vouchers_stock(stock)
            return True
    return False


def get_voucher_from_stock(amount):
    """Stock se voucher nikalo"""
    stock = load_vouchers_stock()
    if amount in stock and len(stock[amount]) > 0:
        code = stock[amount].pop(0)  # First voucher nikalo
        save_vouchers_stock(stock)
        return code
    return None


def record_claimed_voucher(user_id, username, amount, code, points_used):
    """Claimed voucher record karo"""
    claimed = load_claimed_vouchers()
    claimed.append({
        "user_id": user_id,
        "username": username,
        "amount": amount,
        "voucher_code": code,
        "points_used": points_used,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_claimed_vouchers(claimed)


def get_stock_count():
    """Har amount ke liye available vouchers count"""
    stock = load_vouchers_stock()
    return {
        "500": len(stock.get("500", [])),
        "1000": len(stock.get("1000", [])),
        "2000": len(stock.get("2000", []))
    }


def get_user_data(user_id):
    """User ka data get karo"""
    db = load_database()
    user_id_str = str(user_id)
    
    if user_id_str not in db:
        db[user_id_str] = {
            "points": 0,
            "referrals": 0,
            "referred_by": None,
            "verified": False,
            "username": None
        }
        save_database(db)
    
    return db[user_id_str]


def update_user_data(user_id, data):
    """User ka data update karo"""
    db = load_database()
    db[str(user_id)] = data
    save_database(db)


def add_points(user_id, points):
    """User ko points add karo"""
    user_data = get_user_data(user_id)
    user_data["points"] += points
    update_user_data(user_id, user_data)


def deduct_points(user_id, points):
    """User ke points minus karo"""
    user_data = get_user_data(user_id)
    if user_data["points"] >= points:
        user_data["points"] -= points
        update_user_data(user_id, user_data)
        return True
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    
    user = update.effective_user
    user_id = user.id
    
    # Username save karo
    user_data = get_user_data(user_id)
    user_data["username"] = user.username or user.first_name
    update_user_data(user_id, user_data)
    
    # Check for referral code
    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id:
                user_data = get_user_data(user_id)
                if not user_data.get("referred_by"):
                    user_data["referred_by"] = referrer_id
                    update_user_data(user_id, user_data)
        except:
            pass
    
    # Check if already verified
    user_data = get_user_data(user_id)
    if user_data.get("verified"):
        await show_main_menu(update, context)
        return
    
    # Welcome message
    welcome_text = f"""
🙏 नमस्ते {user.first_name}!

आगे बढ़ने के लिए कृपया हमारे Telegram Channel को Join करें 👇

Channel Join करने के बाद "✅ Verify" बटन पर क्लिक करें।
"""
    
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Verify", callback_data="verify")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized! Ye command sirf admin ke liye hai.")
        return
    
    stock = get_stock_count()
    total_users = len(load_database())
    total_claimed = len(load_claimed_vouchers())
    
    admin_text = f"""
👑 Admin Panel

📊 Statistics:
━━━━━━━━━━━━━━━━━
👥 Total Users: {total_users}
🎁 Total Vouchers Claimed: {total_claimed}

📦 Current Stock:
━━━━━━━━━━━━━━━━━
₹500 Vouchers: {stock['500']}
₹1000 Vouchers: {stock['1000']}
₹2000 Vouchers: {stock['2000']}

━━━━━━━━━━━━━━━━━
📝 Commands:

/addvoucher - Add voucher codes
/stock - Check current stock
/users - View all users
/claimed - View claimed vouchers
"""
    
    await update.message.reply_text(admin_text)


async def add_voucher_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add voucher command"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    help_text = """
📝 Add Voucher Codes

Format:
/addvoucher <amount> <code>

Examples:
/addvoucher 500 SHEIN500ABC123
/addvoucher 1000 SHEIN1000XYZ789
/addvoucher 2000 SHEIN2000QWE456

Amount options: 500, 1000, 2000
"""
    
    if len(context.args) < 2:
        await update.message.reply_text(help_text)
        return
    
    amount = context.args[0]
    code = context.args[1].upper()
    
    if amount not in ["500", "1000", "2000"]:
        await update.message.reply_text("❌ Invalid amount! Use: 500, 1000, or 2000")
        return
    
    if add_voucher_to_stock(amount, code):
        stock = get_stock_count()
        await update.message.reply_text(
            f"✅ Voucher Added Successfully!\n\n"
            f"Amount: ₹{amount}\n"
            f"Code: {code}\n\n"
            f"Current Stock: {stock[amount]} vouchers"
        )
    else:
        await update.message.reply_text("❌ Failed to add voucher or code already exists!")


async def check_stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check stock command"""
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    stock = get_stock_count()
    
    stock_text = f"""
📦 Voucher Stock

₹500 Vouchers: {stock['500']} available
₹1000 Vouchers: {stock['1000']} available
₹2000 Vouchers: {stock['2000']} available

Total: {stock['500'] + stock['1000'] + stock['2000']} vouchers
"""
    
    await update.message.reply_text(stock_text)


async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify button handler"""
    
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    
    try:
        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )
        
        if member.status in ['member', 'creator', 'administrator']:
            user_data = get_user_data(user_id)
            
            if not user_data.get("verified"):
                user_data["verified"] = True
                update_user_data(user_id, user_data)
                
                # Referrer ko point do
                if user_data.get("referred_by"):
                    referrer_id = user_data["referred_by"]
                    referrer_data = get_user_data(referrer_id)
                    referrer_data["referrals"] += 1
                    add_points(referrer_id, 1)
                    
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 बधाई हो! {user_name} ने आपके referral link से join किया!\n\n✨ +1 Point मिला!"
                        )
                    except:
                        pass
            
            success_text = f"""
✅ बधाई हो {user_name}!

आपने सफलतापूर्वक Channel Join कर लिया है। 🎉

अब आप निचे दिए गए options का उपयोग कर सकते हैं 👇
"""
            await query.edit_message_text(success_text)
            await show_main_menu_callback(query, context)
            
        else:
            not_joined_text = """
❌ आपने अभी तक Channel Join नहीं किया है!

कृपया पहले Channel Join करें, फिर Verify करें। 👇
"""
            keyboard = [
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ Verify", callback_data="verify")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(not_joined_text, reply_markup=reply_markup)
    
    except Exception as e:
        error_text = """
⚠️ Verification में कोई समस्या आई है।

कृपया सुनिश्चित करें कि:
1. आपने Channel Join किया है
2. Bot को Channel में Admin बनाया गया है

फिर से "Verify" दबाएं।
"""
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu (for message)"""
    user_data = get_user_data(update.effective_user.id)
    points = user_data.get("points", 0)
    
    menu_text = f"""
🏠 Main Menu

💰 आपके पास {points} Points हैं

नीचे दिए गए options में से choose करें:
"""
    
    keyboard = [
        [InlineKeyboardButton("📢 Refer & Earn", callback_data="refer")],
        [InlineKeyboardButton("💎 Check Points", callback_data="check_points")],
        [InlineKeyboardButton("🛍️ Buy Shein Vouchers", callback_data="vouchers")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(menu_text, reply_markup=reply_markup)


async def show_main_menu_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Main menu (for callback)"""
    user_data = get_user_data(query.from_user.id)
    points = user_data.get("points", 0)
    
    menu_text = f"""
🏠 Main Menu

💰 आपके पास {points} Points हैं

नीचे दिए गए options में से choose करें:
"""
    
    keyboard = [
        [InlineKeyboardButton("📢 Refer & Earn", callback_data="refer")],
        [InlineKeyboardButton("💎 Check Points", callback_data="check_points")],
        [InlineKeyboardButton("🛍️ Buy Shein Vouchers", callback_data="vouchers")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(menu_text, reply_markup=reply_markup)


async def handle_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refer & Earn handler"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    referrals = user_data.get("referrals", 0)
    
    bot = await context.bot.get_me()
    bot_username = bot.username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    refer_text = f"""
📢 Refer & Earn Points!

🎁 1 Referral = 1 Point

👥 Total Referrals: {referrals}
💰 Total Points Earned: {referrals}

अपना Referral Link अपने दोस्तों को भेजें:

`{referral_link}`

(Link पर टैप करके copy करें)

जब कोई आपके link से join करेगा, आपको 1 point मिलेगा! ✨
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(refer_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_check_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check Points handler"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    points = user_data.get("points", 0)
    referrals = user_data.get("referrals", 0)
    
    points_text = f"""
💎 Your Points Summary

💰 Total Points: {points}
👥 Total Referrals: {referrals}

━━━━━━━━━━━━━━━━━
🎯 How to Earn More Points:

📢 Refer friends = 1 Point per referral
🎁 More referrals = More points!

━━━━━━━━━━━━━━━━━
🛍️ Redeem Points for Vouchers:

₹500 Voucher = 2 Points
₹1000 Voucher = 4 Points
₹2000 Voucher = 7 Points
"""
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Buy Vouchers", callback_data="vouchers")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(points_text, reply_markup=reply_markup)


async def handle_vouchers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vouchers menu handler"""
    query = update.callback_query
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    points = user_data.get("points", 0)
    stock = get_stock_count()
    
    vouchers_text = f"""
🛍️ Shein Vouchers

💰 आपके पास {points} Points हैं

Available Stock:
━━━━━━━━━━━━━━━━━
🎁 ₹500 Voucher - 2 Points ({stock['500']} available)
🎁 ₹1000 Voucher - 4 Points ({stock['1000']} available)
🎁 ₹2000 Voucher - 7 Points ({stock['2000']} available)

नीचे से voucher select करें:
"""
    
    keyboard = []
    
    # 500 voucher
    if points >= 2 and stock['500'] > 0:
        keyboard.append([InlineKeyboardButton("✅ ₹500 Voucher (2 Points)", callback_data="buy_500")])
    elif points < 2:
        keyboard.append([InlineKeyboardButton("❌ ₹500 (Need 2 Points)", callback_data="need_points")])
    else:
        keyboard.append([InlineKeyboardButton("❌ ₹500 (Out of Stock)", callback_data="out_of_stock")])
    
    # 1000 voucher
    if points >= 4 and stock['1000'] > 0:
        keyboard.append([InlineKeyboardButton("✅ ₹1000 Voucher (4 Points)", callback_data="buy_1000")])
    elif points < 4:
        keyboard.append([InlineKeyboardButton("❌ ₹1000 (Need 4 Points)", callback_data="need_points")])
    else:
        keyboard.append([InlineKeyboardButton("❌ ₹1000 (Out of Stock)", callback_data="out_of_stock")])
    
    # 2000 voucher
    if points >= 7 and stock['2000'] > 0:
        keyboard.append([InlineKeyboardButton("✅ ₹2000 Voucher (7 Points)", callback_data="buy_2000")])
    elif points < 7:
        keyboard.append([InlineKeyboardButton("❌ ₹2000 (Need 7 Points)", callback_data="need_points")])
    else:
        keyboard.append([InlineKeyboardButton("❌ ₹2000 (Out of Stock)", callback_data="out_of_stock")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(vouchers_text, reply_markup=reply_markup)


async def handle_buy_voucher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Voucher purchase handler"""
    query = update.callback_query
    
    voucher_type = query.data.replace("buy_", "")
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    points = user_data.get("points", 0)
    username = user_data.get("username", "User")
    
    price = VOUCHER_PRICES[voucher_type]
    amount = f"₹{voucher_type}"
    
    # Check points
    if points < price:
        await query.answer(f"❌ आपके पास पर्याप्त points नहीं हैं!", show_alert=True)
        return
    
    # Check stock
    voucher_code = get_voucher_from_stock(voucher_type)
    if not voucher_code:
        await query.answer("❌ Sorry! This voucher is out of stock!", show_alert=True)
        return
    
    await query.answer()
    
    # Points deduct karo
    if deduct_points(user_id, price):
        # Record claimed voucher
        record_claimed_voucher(user_id, username, voucher_type, voucher_code, price)
        
        success_text = f"""
🎉 बधाई हो!

आपने {amount} का REAL Shein Voucher successfully claim कर लिया है!

━━━━━━━━━━━━━━━━━
🎁 आपका Voucher Code:

`{voucher_code}`

━━━━━━━━━━━━━━━━━
💰 {price} Points deducted
💎 Remaining Points: {points - price}

━━━━━━━━━━━━━━━━━
📝 How to Use:

1. Shein app/website पर जाएं
2. Checkout के समय voucher code डालें
3. {amount} की discount पाएं! 🎊

⚠️ Important:
• Ye REAL voucher code hai
• इसे safe रखें
• Screenshot le sakte hain
• Code केवल एक बार दिखाया जाएगा
"""
        
        keyboard = [
            [InlineKeyboardButton("🛍️ Buy More Vouchers", callback_data="vouchers")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Admin ko notification bhejo
        try:
            stock = get_stock_count()
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"📊 Voucher Claimed!\n\n"
                     f"User: {username} ({user_id})\n"
                     f"Amount: {amount}\n"
                     f"Code: {voucher_code}\n\n"
                     f"Remaining Stock:\n"
                     f"₹500: {stock['500']}\n"
                     f"₹1000: {stock['1000']}\n"
                     f"₹2000: {stock['2000']}"
            )
        except:
            pass


async def handle_need_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Not enough points handler"""
    query = update.callback_query
    await query.answer("❌ आपके पास पर्याप्त points नहीं हैं! अधिक referrals करें।", show_alert=True)


async def handle_out_of_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Out of stock handler"""
    query = update.callback_query
    await query.answer("❌ Sorry! This voucher is currently out of stock. Please try again later.", show_alert=True)


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Back to menu handler"""
    query = update.callback_query
    await query.answer()
    
    user_data = get_user_data(query.from_user.id)
    points = user_data.get("points", 0)
    
    menu_text = f"""
🏠 Main Menu

💰 आपके पास {points} Points हैं

नीचे दिए गए options में से choose करें:
"""
    
    keyboard = [
        [InlineKeyboardButton("📢 Refer & Earn", callback_data="refer")],
        [InlineKeyboardButton("💎 Check Points", callback_data="check_points")],
        [InlineKeyboardButton("🛍️ Buy Shein Vouchers", callback_data="vouchers")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(menu_text, reply_markup=reply_markup)


def main():
    """Bot ko start karo"""
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🤖 REAL Shein Voucher Bot Starting...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot Token: Configured")
    print(f"✅ Channel ID: {CHANNEL_ID}")
    print(f"✅ Admin ID: {ADMIN_USER_ID}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Initial stock check
    stock = get_stock_count()
    print(f"📦 Current Stock:")
    print(f"   ₹500: {stock['500']} vouchers")
    print(f"   ₹1000: {stock['1000']} vouchers")
    print(f"   ₹2000: {stock['2000']} vouchers")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # User handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(verify_membership, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(handle_refer, pattern="^refer$"))
    app.add_handler(CallbackQueryHandler(handle_check_points, pattern="^check_points$"))
    app.add_handler(CallbackQueryHandler(handle_vouchers, pattern="^vouchers$"))
    app.add_handler(CallbackQueryHandler(handle_buy_voucher, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(handle_need_points, pattern="^need_points$"))
    app.add_handler(CallbackQueryHandler(handle_out_of_stock, pattern="^out_of_stock$"))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern="^menu$"))
    
    # Admin handlers
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addvoucher", add_voucher_command))
    app.add_handler(CommandHandler("stock", check_stock_command))
    
    print("✅ Bot Successfully Started! 🎉")
    print("💰 Points System: Active")
    print("📢 Referral System: Active")
    print("🎁 REAL Voucher System: Active")
    print("\n⚡ Bot is running...")
    print("👑 Admin commands available")
    print("🛑 Press Ctrl+C to stop\n")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
