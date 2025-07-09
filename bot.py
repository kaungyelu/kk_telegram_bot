import os
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_deepseek_response(api_key, user_message):
    try:
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
        
        # Timeout ထည့်ခြင်း
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        # HTTP status code စစ်ဆေးခြင်း
        if response.status_code != 200:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return f"⚠️ API Error ({response.status_code}): {response.text[:200]}"
        
        response_data = response.json()
        
        # API response structure စစ်ဆေးခြင်း
        if 'choices' not in response_data or len(response_data['choices']) == 0:
            logger.error(f"Invalid API response: {response_data}")
            return "⚠️ Invalid API response structure"
            
        return response_data['choices'][0]['message']['content']
        
    except requests.exceptions.Timeout:
        logger.error("API Request Timeout")
        return "⏳ API ချိတ်ဆက်မှု ကြာနေပါသည်။ နောက်မှထပ်ကြိုးစားပါ"
    except requests.exceptions.RequestException as e:
        logger.error(f"Request Exception: {str(e)}")
        return f"❌ Network Error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        return f"❌ System Error: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        logger.info(f"Received message: {user_input}")
        
        api_key = os.getenv("DEEPSEEK_API_KEY")
        
        if not api_key:
            await update.message.reply_text("❌ DeepSeek API key not configured")
            logger.error("DeepSeek API key not found in environment variables")
            return
            
        # Skip empty messages
        if len(user_input.strip()) < 2:
            return
            
        # Get AI response
        ai_response = get_deepseek_response(api_key, user_input)
        
        # Truncate long messages
        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "..."
            
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"Handle message error: {str(e)}")
        await update.message.reply_text(f"⚠️ Bot processing error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 kkuserအစားဖြေဆိုပေးမဲ့ Bot စတင်ပါပြီ!\nGroup ထဲမှာ မေးခွန်းမေးနိုင်ပါတယ်")

async def check_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """API connection test command"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        await update.message.reply_text("❌ API key not found in environment variables")
        return
        
    try:
        # Simple API test
        url = "https://api.deepseek.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            await update.message.reply_text("✅ API connection successful!")
        else:
            await update.message.reply_text(f"⚠️ API connection failed ({response.status_code})")
    except Exception as e:
        await update.message.reply_text(f"❌ API test failed: {str(e)}")

if __name__ == "__main__":
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        exit(1)
        
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("api_test", check_api))  # New API test command
    
    # Group message handler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        handle_message
    ))
    
    logger.info("Bot starting...")
    app.run_polling()
