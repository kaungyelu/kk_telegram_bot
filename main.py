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
datelist = []
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

# ✅ Updated Message Handler with Power Entry
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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
        if "-" in entry:
            try:
                num_str, amt_str = entry.split("-")
                num = int(num_str)
                amt = int(amt_str)
                ledger[num] = ledger.get(num, 0) + amt
                user_data[user.username][key].append((num, amt))
                added += amt
            except:
                continue
        else:
            try:
                num = int(entry)
                amt = 500
                ledger[num] = ledger.get(num, 0) + amt
                user_data[user.username][key].append((num, amt))
                added += amt
            except:
                continue

    await update.message.reply_text(f"{added} လို")

async def ledger_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📒 Ledger Summary"]
    for i in range(100):
        total = ledger.get(i, 0)
        lines.append(f"{i:02} ➤ {total if total else ''}")
    await update.message.reply_text("\n".join(lines))

async def break_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        limit = int(context.args[0])
        msg = ["📌 Over Limit:"]
        for k, v in ledger.items():
            if v > limit:
                msg.append(f"{k:02} ➤ {v - limit}")
        await update.message.reply_text("\n".join(msg))
    except:
        await update.message.reply_text("Limit amount ထည့်ပါ")

async def overbuy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("User name ထည့်ပါ")
        return
    user = context.args[0]
    overbuy_list[user] = ledger.copy()
    await update.message.reply_text(f"{user} အတွက် overbuy စာရင်းပြထားပါတယ်")

async def pnumber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global pnumber_value
    try:
        pnumber_value = int(context.args[0])
        msg = []
        for user, records in user_data.items():
            total = 0
            for d in records:
                for num, amt in records[d]:
                    if num == pnumber_value:
                        total += amt
            msg.append(f"{user}: {pnumber_value} ➤ {total}")
        await update.message.reply_text("\n".join(msg))
    except:
        await update.message.reply_text("ဂဏန်းမှန်မှန်ထည့်ပါ")

async def comandza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = list(user_data.keys())
    keyboard = [[InlineKeyboardButton(u, callback_data=f"comza:{u}")] for u in users]
    await update.message.reply_text("User ကိုရွေးပါ", reply_markup=InlineKeyboardMarkup(keyboard))

async def comza_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['selected_user'] = query.data.split(":")[1]
    await query.edit_message_text(f"{context.user_data['selected_user']} ကိုရွေးထားသည်။ 15/80 လို့ထည့်ပါ။")

async def comza_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = context.user_data.get('selected_user')
    if user and '/' in update.message.text:
        try:
            com, za = map(int, update.message.text.split('/'))
            com_data[user] = com
            za_data[user] = za
            await update.message.reply_text(f"Com {com}%, Za {za} မှတ်ထားပြီး")
        except:
            await update.message.reply_text("မှန်မှန်ရေးပါ (ဥပမာ 15/80)")

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = []
    for user, records in user_data.items():
        total = sum(amt for d in records for _, amt in records[d])
        com = com_data.get(user, 0)
        za = za_data.get(user, 0)
        after_com = total - (total * com) // 100

        pamt = 0
        for d in records:
            for num, amt in records[d]:
                if num == pnumber_value:
                    pamt += amt

        win = pamt * za
        net = after_com - win
        status = "ဒိုင်ကပေးရမည်" if net < 0 else "ဒိုင်ကရမည်"

        msg.append(
            f"{user}\nTotal: {total}\nCom({com}%) ➤ {total * com // 100}\nAfter Com: {after_com}\n"
            f"Pnumber({pnumber_value}) ➤ {pamt}\nZa({za}) ➤ {win}\nResult: {net} ({status})\n---"
        )

    await update.message.reply_text("\n".join(msg))

async def tsent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in user_data:
        await update.message.reply_text(f"{user} အတွက်စာရင်းပေးပို့ပြီး")

async def alldata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = []
    for user in user_data:
        msg.append(user)
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
