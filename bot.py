import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# DeepSeek API
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
        response.raise_for_status()  # Raise exception for HTTP errors
        response_data = response.json()
        
        # Check if the response has choices
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            logger.error("No choices in response: %s", response_data)
            return "⚠️ ဖြေဆိုရာတွင် ပြဿနာရှိပါသည် (အဖြေမရှိပါ)"
            
    except requests.exceptions.RequestException as e:
        logger.error("DeepSeek API Request failed: %s", str(e))
        return "🔌 API ချိတ်ဆက်မှုမအောင်မြင်ပါ"
    except Exception as e:
        logger.error("DeepSeek Error: %s", str(e))
        return "⚠️ ဖြေဆိုရာတွင် အမှားတစ်ခုဖြစ်နေပါသည်"

# Group message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # Skip short messages (optional)
    if len(user_input.strip()) < 2:
        return
    
    # Get AI response
    ai_response = get_deepseek_response(api_key, user_input)
    await update.message.reply_text(ai_response)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 KKuserအစား‌ဖြေပေးမယ့်   Bot စတင်ပါပြီ!\nGroup ထဲမှာ မေးခွန်းမေးနိုင်ပါတယ်")

# Help command
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🔧 Admin များအတွက်:
1. Bot ကို Admin အဖြစ်ခန့်ပါ
2. Privacy mode ပိတ်ပါ: BotFather မှာ /setprivacy -> Disable
    """
    await update.message.reply_text(help_text)

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN not set!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    
    # Group messages - only in groups and supergroups
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        handle_message
    ))
    
    logger.info("Bot started polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
