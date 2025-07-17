import os
import requests
import logging
import time
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User settings storage
USER_PROVIDER = {}  # {user_id: 'deepseek'/'gemini'/'openrouter'}
USER_COOLDOWN = {}  # {user_id: last_request_time}
REQUEST_COOLDOWN = 15  # seconds

class AIProvider:
    @staticmethod
    def get_response(provider: str, user_message: str) -> str:
        """Get response from selected provider"""
        try:
            if provider == 'deepseek':
                return AIProvider.deepseek(user_message)
            elif provider == 'gemini':
                return AIProvider.gemini(user_message)
            elif provider == 'openrouter':
                return AIProvider.openrouter(user_message)
            else:
                raise ValueError("Invalid provider selected")
        except Exception as e:
            logger.error(f"{provider} failed: {str(e)}")
            # Try fallback to other providers
            for fallback in ['deepseek', 'gemini', 'openrouter']:
                if fallback != provider:
                    try:
                        return AIProvider.fallback(fallback, user_message)
                    except:
                        continue
            raise Exception("All providers failed")

    @staticmethod
    def deepseek(user_message: str) -> str:
        """DeepSeek API"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DeepSeek API key not set")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.5,
            "max_tokens": 1000
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"DeepSeek API Error ({response.status_code}): {error_msg}")
        
        return response.json()['choices'][0]['message']['content']

    @staticmethod
    def gemini(user_message: str) -> str:
        """Gemini 2.5 API"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Gemini API key not set")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_message}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 1000
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"Gemini API Error ({response.status_code}): {error_msg}")
        
        return response.json()['candidates'][0]['content']['parts'][0]['text']

    @staticmethod
    def openrouter(user_message: str) -> str:
        """OpenRouter API"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise Exception("OpenRouter API key not set")
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://kkuser-bot.com",
            "X-Title": "KKuser Assistant"
        }
        
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"OpenRouter Error ({response.status_code}): {error_msg}")
        
        return response.json()['choices'][0]['message']['content']

    @staticmethod
    def fallback(provider: str, user_message: str) -> str:
        """Fallback to another provider"""
        if provider == 'deepseek':
            return AIProvider.deepseek(user_message)
        elif provider == 'gemini':
            return AIProvider.gemini(user_message)
        elif provider == 'openrouter':
            return AIProvider.openrouter(user_message)
        else:
            raise ValueError("Invalid fallback provider")

# ===================== Bot Commands =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot စတင်ခြင်း"""
    user_id = update.message.from_user.id
    USER_PROVIDER[user_id] = 'deepseek'  # Default provider
    
    await update.message.reply_text(
        "🤖 KKuser ဆရာကြီး၏ တပည့်ဘော့မှ ကြိုဆိုပါတယ်!\n"
        "အောက်ပါ command များဖြင့် စတင်အသုံးပြုနိုင်ပါသည်:\n\n"
        "/setprovider - AI ပေးသူပြောင်းရန်\n"
        "/getprovider - လက်ရှိသုံးနေသော AI ကြည့်ရန်\n"
        "/help - အကူအညီများကြည့်ရန်"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အကူအညီ command"""
    help_text = (
        "🛠️ အသုံးပြုနည်း:\n"
        "1. /setprovider ဖြင့် AI ပေးသူရွေးပါ\n"
        "2. Group ထဲတွင် မေးခွန်းမေးပါ\n\n"
        "📋 Commands:\n"
        "/start - Bot စတင်ရန်\n"
        "/setprovider - AI ပေးသူပြောင်းရန် (deepseek, gemini, openrouter)\n"
        "/getprovider - လက်ရှိသုံးနေသော AI ကြည့်ရန်\n"
        "/ping - Bot အလုပ်လုပ်မလုပ်စစ်ဆေးရန်\n"
        "/help - အကူအညီ"
    )
    await update.message.reply_text(help_text)

async def set_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set AI provider"""
    user_id = update.message.from_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ provider အမျိုးအစားထည့်ပါ။ ဥပမာ:\n"
            "/setprovider deepseek\n"
            "/setprovider gemini\n"
            "/setprovider openrouter"
        )
        return
    
    provider = args[0].lower()
    valid_providers = ['deepseek', 'gemini', 'openrouter']
    
    if provider in valid_providers:
        USER_PROVIDER[user_id] = provider
        await update.message.reply_text(f"✅ AI provider ကို {provider} အဖြစ်ပြောင်းလိုက်ပါပြီ!")
    else:
        await update.message.reply_text(
            f"❌ {provider} သည် မရှိသော provider ဖြစ်ပါသည်။\n"
            f"ရနိုင်သော provider များ: {', '.join(valid_providers)}"
        )

async def get_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current AI provider"""
    user_id = update.message.from_user.id
    provider = USER_PROVIDER.get(user_id, 'deepseek')
    await update.message.reply_text(f"🔧 လက်ရှိသုံးစွဲနေသော AI provider: {provider}")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot အလုပ်လုပ်မလုပ် စစ်ဆေးခြင်း"""
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pong!...")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"🏓 Pong! Latency: {latency}ms")

# ===================== Message Handling =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Group ထဲက မက်ဆေ့ဂျ်များကို ကိုင်တွယ်ခြင်း"""
    try:
        user_id = update.message.from_user.id
        current_time = time.time()
        
        # Cooldown စစ်ဆေးခြင်း
        if user_id in USER_COOLDOWN:
            elapsed = current_time - USER_COOLDOWN[user_id]
            if elapsed < REQUEST_COOLDOWN:
                await update.message.reply_text(
                    f"⏳ ကျေးဇူးပြု၍ {REQUEST_COOLDOWN - int(elapsed)} စက္ကန့်စောင့်ပါ"
                )
                return
        
        USER_COOLDOWN[user_id] = current_time
        
        # Get or set default provider
        provider = USER_PROVIDER.get(user_id, 'deepseek')
        user_input = update.message.text
        
        # AI ကို မေးခွန်းမေးခြင်း
        thinking_msg = await update.message.reply_text(f"🤔 {provider} ဖြင့် အဖြေရှာနေပါသည်...")
        
        try:
            ai_response = AIProvider.get_response(provider, user_input)
        except Exception as e:
            logger.error(f"All providers failed: {str(e)}")
            ai_response = "⚠️ ဆောရီးပါ၊ လက်ရှိတွင် AI များအားလုံးအလုပ်မလုပ်နိုင်ပါ။ ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားပါ။"
        
        # တုံ့ပြန်ချက် လှီးဖြတ်ခြင်း
        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "..."
        
        # Signature ထည့်ခြင်း
        signature = "\n\n- KKuser ၏ တပည့်တစ်ဦးမှ ဖြေဆိုပါသည် -"
        final_response = ai_response + signature
        
        await thinking_msg.delete()
        await update.message.reply_text(final_response)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        error_msg = (
            "⚠️ အဖြေရယူရာတွင် ပြဿနာတစ်ခုဖြစ်နေပါသည်။\n"
            "ကျေးဇူးပြု၍ မိနစ်အနည်းငယ်ကြာမှ ထပ်ကြိုးစားပါ"
        )
        await update.message.reply_text(error_msg)

# ===================== Main Application =====================
def main():
    # Bot token စစ်ဆေးခြင်း
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        exit(1)
    
    # Bot application ဖန်တီးခြင်း
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setprovider", set_provider))
    app.add_handler(CommandHandler("getprovider", get_provider))
    app.add_handler(CommandHandler("ping", ping))
    
    # Group message handler
    app.add_handler(MessageHandler(
        filters.TEXT & 
        ~filters.COMMAND & 
        (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        handle_message
    ))
    
    # Bot စတင်ခြင်း
    logger.info("🤖 KKuser ၏ တပည့်ဘော့စ် စတင်နေပါပြီ...")
    app.run_polling()

if __name__ == "__main__":
    main()
