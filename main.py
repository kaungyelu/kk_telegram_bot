import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from datetime import datetime, time

# Load .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Globals
admin_id = None
user_data = {}
ledger = {}
za_data = {}
com_data = {}
pnumber_value = None
date_control = {}
overbuy_list = {}

# Utility
def get_time_segment():
    now = datetime.now().time()
    return "AM" if now < time(12, 0) else "PM"

def get_current_date_key():
    now = datetime.now()
    return f"{now.strftime('%d/%m/%Y')} {get_time_segment()}"

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_id
    admin_id = update.effective_user.id
    await update.message.reply_text("🤖 Bot started.")

async def dateopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = get_current_date_key()
    date_control[key] = True
    await update.message.reply_text(f"{key} စာရင်းဖွင့်ပြီးပါပြီ")

async def dateclose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = get_current_date_key()
    date_control[key] = False
    await update.message.reply_text(f"{key} စာရင်းပိတ်လိုက်ပါပြီ")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user.username:
        await update.message.reply_text("ကျေးဇူးပြု၍ Telegram username သတ်မှတ်ပါ")
        return

    key = get_current_date_key()
    if not date_control.get(key, False):
        await update.message.reply_text("စာရင်းပိတ်ထားပါသည်")
        return

    text = update.message.text
    entries = text.split()
    added = 0

    if user.username not in user_data:
        user_data[user.username] = {}
    if key not in user_data[user.username]:
        user_data[user.username][key] = []

    for entry in entries:
        try:
            if "-" in entry:
                num_str, amt_str = entry.split("-")
                num = int(num_str)
                amt = int(amt_str)
            else:
                num = int(entry)
                amt = 500  # Default amount
            
            # Validate number range
            if num < 0 or num > 99:
                raise ValueError("Invalid number")
                
            ledger[num] = ledger.get(num, 0) + amt
            user_data[user.username][key].append((num, amt))
            added += amt
        except Exception as e:
            logging.error(f"Error processing entry: {entry} - {str(e)}")
            continue

    if added > 0:
        await update.message.reply_text(f"{added} လို")
    else:
        await update.message.reply_text("အချက်အလက်များကိုစစ်ဆေးပါ")

async def ledger_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📒 Ledger Summary"]
    for i in range(100):
        total = ledger.get(i, 0)
        if total > 0:  # Only show numbers with bets
            lines.append(f"{i:02} ➤ {total}")
    await update.message.reply_text("\n".join(lines))

async def break_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Usage: /break [limit]")
            return
            
        limit = int(context.args[0])
        msg = ["📌 Over Limit:"]
        for k, v in ledger.items():
            if v > limit:
                msg.append(f"{k:02} ➤ {v - limit}")
        
        if len(msg) == 1:
            await update.message.reply_text("ဘယ်ဂဏန်းမှ limit မကျော်ပါ")
        else:
            await update.message.reply_text("\n".join(msg))
    except (ValueError, IndexError):
        await update.message.reply_text("Limit amount ထည့်ပါ (ဥပမာ: /break 5000)")

async def overbuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /overbuy [username]")
        return
        
    user = context.args[0]
    overbuy_list[user] = ledger.copy()
    await update.message.reply_text(f"{user} အတွက် overbuy စာရင်းပြထားပါတယ်")

async def pnumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pnumber_value
    try:
        if not context.args:
            await update.message.reply_text("Usage: /pnumber [number]")
            return
            
        pnumber_value = int(context.args[0])
        if pnumber_value < 0 or pnumber_value > 99:
            await update.message.reply_text("ဂဏန်းကို 0 နှင့် 99 ကြားထည့်ပါ")
            return
            
        msg = []
        for user, records in user_data.items():
            total = 0
            for date_key in records:
                for num, amt in records[date_key]:
                    if num == pnumber_value:
                        total += amt
            if total > 0:
                msg.append(f"{user}: {pnumber_value} ➤ {total}")
        
        if msg:
            await update.message.reply_text("\n".join(msg))
        else:
            await update.message.reply_text(f"{pnumber_value} အတွက် လောင်းကြေးမရှိပါ")
    except (ValueError, IndexError):
        await update.message.reply_text("ဂဏန်းမှန်မှန်ထည့်ပါ (ဥပမာ: /pnumber 15)")

async def comandza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("လက်ရှိ user မရှိပါ")
        return
        
    users = list(user_data.keys())
    keyboard = [[InlineKeyboardButton(u, callback_data=f"comza:{u}")] for u in users]
    await update.message.reply_text("User ကိုရွေးပါ", reply_markup=InlineKeyboardMarkup(keyboard))

async def comza_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['selected_user'] = query.data.split(":")[1]
    await query.edit_message_text(f"{context.user_data['selected_user']} ကိုရွေးထားသည်။ 15/80 လို့ထည့်ပါ")

async def comza_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = context.user_data.get('selected_user')
    if not user:
        # Not in commission setting mode, process as normal message
        await handle_message(update, context)
        return
        
    text = update.message.text
    if '/' in text:
        try:
            parts = text.split('/')
            if len(parts) != 2:
                raise ValueError
            
            com = int(parts[0])
            za = int(parts[1])
            
            if com < 0 or com > 100 or za < 0:
                raise ValueError
                
            com_data[user] = com
            za_data[user] = za
            del context.user_data['selected_user']  # Clear state
            await update.message.reply_text(f"Com {com}%, Za {za} မှတ်ထားပြီး")
        except:
            await update.message.reply_text("မှန်မှန်ရေးပါ (ဥပမာ: 15/80)")
    else:
        await update.message.reply_text("ဖော်မတ်မှားနေပါသည်။ 15/80 လို့ထည့်ပါ")

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("လက်ရှိစာရင်းမရှိပါ")
        return
        
    if pnumber_value is None:
        await update.message.reply_text("ကျေးဇူးပြု၍ /pnumber ဖြင့် power number သတ်မှတ်ပါ")
        return
        
    msg = []
    for user, records in user_data.items():
        total_amt = 0
        pamt = 0
        
        # Calculate totals
        for date_key in records:
            for num, amt in records[date_key]:
                total_amt += amt
                if num == pnumber_value:
                    pamt += amt
        
        # Get commission and za rates (default to 0 if not set)
        com = com_data.get(user, 0)
        za = za_data.get(user, 0)
        
        commission_amt = (total_amt * com) // 100
        after_com = total_amt - commission_amt
        win_amt = pamt * za
        
        net = after_com - win_amt
        status = "ဒိုင်ကပေးရမည်" if net < 0 else "ဒိုင်ကရမည်"
        
        user_report = (
            f"{user}\n"
            f"Total: {total_amt}\n"
            f"Com({com}%) ➤ {commission_amt}\n"
            f"After Com: {after_com}\n"
            f"Pnumber({pnumber_value}) ➤ {pamt}\n"
            f"Za({za}) ➤ {win_amt}\n"
            f"Result: {abs(net)} ({status})\n"
            "---"
        )
        msg.append(user_report)

    await update.message.reply_text("\n".join(msg))

async def tsent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("လက်ရှိ user မရှိပါ")
        return
        
    for user in user_data:
        await update.message.reply_text(f"{user} အတွက်စာရင်းပေးပို့ပြီး")

async def alldata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_data:
        await update.message.reply_text("လက်ရှိစာရင်းမရှိပါ")
        return
        
    msg = ["👥 Registered Users:"]
    msg.extend(user_data.keys())
    await update.message.reply_text("\n".join(msg))

# Main
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

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

    app.add_handler(CallbackQueryHandler(comza_input, pattern=r"^comza:"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), comza_text))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()
