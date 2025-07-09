import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# DeepSeek API ကိုအသုံးပြုပြီး အဖြေရယူခြင်း
def get_deepseek_response(api_key, user_message):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": user_message}],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    except Exception as e:
        print(f"DeepSeek API Error: {str(e)}")
        return "ဖြေဆိုရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်။ ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားပါ။"

# Group ထဲရှိ မည်သည့်စာကိုမဆို ဖြေဆိုမည်
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # DeepSeek API ခေါ်ယူခြင်း
    bot_response = get_deepseek_response(api_key, user_message)
    await update.message.reply_text(bot_response)

# Bot စတင်ခြင်း
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
👋 မင်္ဂလာပါ! 
ကျွန်တော်က KKuserအစားမေးသမျှဖြေပေးမဲ့    Telegram bot ပါ။
Group ထဲမှာမေးသမျှမေးခွန်းတွေကို အဖြေပေးနိုင်ပါတယ်။
    """)

# Admin များအတွက် အကူအညီ command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🛠️ Admin များအတွက် အသုံးပြုနည်း:
1. Bot ကို group ထဲထည့်ပါ
2. Bot ကို Admin အဖြစ်ခန့်ပါ
3. Group settings > Privacy mode: OFF လုပ်ပါ
4. /setprivacy ကိုသုံးပြီး Disable လုပ်ပါ
    """
    await update.message.reply_text(help_text)

if __name__ == "__main__":
    # Environment variables မှ token ရယူခြင်း
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    # Bot application စတင်ခြင်း
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    
    # Group messages handler (MUST have privacy mode disabled)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))
    
    # Bot စတင်အလုပ်လုပ်စေခြင်း
    print("🤖 KKuserBot is running...")
    app.run_polling()
