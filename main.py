import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from datetime import datetime, time, timedelta, timezone

# Load .env token
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Add ADMIN_ID in .env

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Timezone
MMT = timezone(timedelta(hours=6, minutes=30))

# Globals
user_data = {}          # {user_id: {date_key: [(num, amount)]}}
ledger = {}             # {num: total_amount}
za_data = {}            # {user_id: za_value}
com_data = {}           # {user_id: com_percentage}
pnumber_value = None    # Current pnumber
date_control = {}       # {date_key: bool}
overbuy_list = {}       # {user_id: ledger_copy}
user_names = {}         # {user_id: display_name}

# Helper functions
def get_time_segment():
    now = datetime.now(MMT).time()
    return "AM" if now < time(12, 0) else "PM"

def get_current_date_key():
    now = datetime.now(MMT)
    return f"{now.strftime('%d/%m/%Y')} {get_time_segment()}"

def parse_numbers(text):
    return list(map(int, re.findall(r'\d{2}', text)))

def is_admin(user_id):
    return user_id == ADMIN_ID

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_names[user.id] = user.username or user.first_name
    await update.message.reply_text("🤖 Bot started.")

async def dateopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
    key = get_current_date_key()
    date_control[key] = True
    await update.message.reply_text(f"{key} စာရင်းဖွင့်ပြီးပါပြီ")

async def dateclose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
    key = get_current_date_key()
    date_control[key] = False
    await update.message.reply_text(f"{key} စာရင်းပိတ်လိုက်ပါပြီ")

async def handle_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    key = get_current_date_key()
    
    # Store user display name
    if user_id not in user_names:
        user_names[user_id] = user.username or user.first_name
    
    # Check date control
    if not date_control.get(key, False):
        await update.message.reply_text("စာရင်းပိတ်ထားပါသည်")
        return

    # Process numbers
    numbers = parse_numbers(update.message.text)
    if not numbers:
        return
    
    # Initialize user data
    if user_id not in user_data:
        user_data[user_id] = {}
    if key not in user_data[user_id]:
        user_data[user_id][key] = []
    
    # Update ledger and user data
    for num in numbers:
        bet_amount = 500  # Fixed amount per number
        ledger[num] = ledger.get(num, 0) + bet_amount
        user_data[user_id][key].append((num, bet_amount))
    
    total_bet = len(numbers) * 500
    await update.message.reply_text(f"{total_bet} လို")

async def ledger_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    lines = ["📒 Ledger Summary"]
    for i in range(100):
        total = ledger.get(i, 0)
        if total > 0:
            lines.append(f"{i:02} ➤ {total}")
    await update.message.reply_text("\n".join(lines))

async def break_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    try:
        limit = int(context.args[0])
        msg = ["📌 Over Limit:"]
        for num, total in ledger.items():
            if total > limit:
                msg.append(f"{num:02} ➤ {total - limit}")
        await update.message.reply_text("\n".join(msg))
    except:
        await update.message.reply_text("Limit amount ထည့်ပါ (ဥပမာ: /break 10000)")

async def overbuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("User ID ထည့်ပါ (ဥပမာ: /overbuy 123456789)")
        return
        
    try:
        user_id = int(context.args[0])
        overbuy_list[user_id] = ledger.copy()
        await update.message.reply_text(f"{user_names.get(user_id, user_id)} အတွက် overbuy စာရင်းပြထားပါတယ်")
    except:
        await update.message.reply_text("ဂဏန်းမှန်မှန်ထည့်ပါ")

async def pnumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    global pnumber_value
    try:
        pnumber_value = int(context.args[0])
        msg = []
        for user_id, records in user_data.items():
            total = 0
            for date_key in records:
                for num, amt in records[date_key]:
                    if num == pnumber_value:
                        total += amt
            if total > 0:
                msg.append(f"{user_names.get(user_id, user_id)}: {pnumber_value} ➤ {total}")
        await update.message.reply_text("\n".join(msg) if msg else "ဒေတာမရှိပါ")
    except:
        await update.message.reply_text("ဂဏန်းမှန်မှန်ထည့်ပါ (ဥပမာ: /pnumber 12)")

async def comandza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    if not user_data:
        await update.message.reply_text("အသုံးပြုသူမရှိသေးပါ")
        return
        
    keyboard = []
    for user_id in user_data:
        display_name = user_names.get(user_id, f"User_{user_id}")
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"comza:{user_id}")])
    
    await update.message.reply_text(
        "User ကိုရွေးပါ", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def comza_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split(":")[1])
    context.user_data['selected_user_id'] = user_id
    display_name = user_names.get(user_id, f"User_{user_id}")
    await query.edit_message_text(f"{display_name} ကိုရွေးထားသည်။ Com/Za ထည့်ပါ (ဥပမာ: 15/80)")

async def comza_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if 'selected_user_id' not in context.user_data:
        return
        
    try:
        text = update.message.text
        if '/' not in text:
            raise ValueError
            
        com_str, za_str = text.split('/')
        com = int(com_str.strip())
        za = int(za_str.strip())
        user_id = context.user_data['selected_user_id']
        
        com_data[user_id] = com
        za_data[user_id] = za
        
        del context.user_data['selected_user_id']
        display_name = user_names.get(user_id, f"User_{user_id}")
        await update.message.reply_text(f"{display_name} - Com {com}%, Za {za} မှတ်ထားပြီး")
    except:
        await update.message.reply_text("မှားယွင်းနေပါသည်။ ဥပမာ: 15/80")

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    if not user_data:
        await update.message.reply_text("ဒေတာမရှိသေးပါ")
        return
        
    global pnumber_value
    msg = []
    
    for user_id, records in user_data.items():
        # Calculate total bets
        user_total = sum(amt for date_records in records.values() for _, amt in date_records)
        
        # Get com/za values
        com = com_data.get(user_id, 0)
        za = za_data.get(user_id, 0)
        
        # Calculate commission
        commission = (user_total * com) // 100
        after_com = user_total - commission
        
        # Calculate winning amount
        pamt = 0
        if pnumber_value is not None:
            for date_records in records.values():
                for num, amt in date_records:
                    if num == pnumber_value:
                        pamt += amt
        
        win_amount = pamt * za
        net_amount = after_com - win_amount
        status = "ဒိုင်ကပေးရမည်" if net_amount < 0 else "ဒိုင်ကရမည်"
        
        # Prepare message
        display_name = user_names.get(user_id, f"User_{user_id}")
        user_msg = [
            f"👤 {display_name}",
            f"စုစုပေါင်း: {user_total}",
            f"ကော်မရှင်({com}%): {commission}",
            f"ကော်မအပြီး: {after_com}",
            f"ပါဝါနံပါတ်({pnumber_value or '-'}): {pamt}",
            f"ဇာ({za}): {win_amount}",
            f"အသားတင်: {abs(net_amount)} ({status})",
            "------------------"
        ]
        msg.append("\n".join(user_msg))
    
    await update.message.reply_text("\n".join(msg))

async def tsent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    for user_id in user_data:
        display_name = user_names.get(user_id, f"User_{user_id}")
        await update.message.reply_text(f"{display_name} အတွက်စာရင်းပေးပို့ပြီး")

async def alldata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Permission denied.")
        return
        
    msg = ["အသုံးပြုသူစာရင်း:"]
    for user_id in user_data:
        display_name = user_names.get(user_id, f"User_{user_id}")
        msg.append(f"- {display_name} (ID: {user_id})")
    
    await update.message.reply_text("\n".join(msg))

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dateopen", dateopen))
    app.add_handler(CommandHandler("dateclose", dateclose))
    app.add_handler(CommandHandler("ledger", ledger_summary))
    app.add_handler(CommandHandler("break", break_command))
    app.add_handler(CommandHandler("overbuy", overbuy))
    app.add_handler(CommandHandler("pnumber", pnumber))
    app.add_handler(CommandHandler("comandza", comandza))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("tsent", tsent))
    app.add_handler(CommandHandler("alldata", alldata))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(comza_input, pattern=r"^comza:"))
    
    # Message handlers
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
        comza_text
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_bet
    ))
    
    app.run_polling()
