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

# Logging စနစ်ကို setup လုပ်ခြင်း
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# အသုံးပြုမှု ကန့်သတ်ချက်
USER_COOLDOWN = {}  # {user_id: last_request_time}
REQUEST_COOLDOWN = 15  # စက္ကန့်

class AIProvider:
    @staticmethod
    def get_response(user_message: str) -> str:
        """AI provider ကို အလိုအလျောက် ပြောင်းသုံးခြင်း"""
        try:
            return AIProvider.deepseek(user_message)
        except Exception as e:
            logger.error(f"DeepSeek failed: {str(e)}")
            return AIProvider.openrouter(user_message)

    @staticmethod
    def deepseek(user_message: str) -> str:
        """DeepSeek API သုံးခြင်း - မြန်မာလိုပဲဖြေရန်"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DeepSeek API key not set")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # မြန်မာလိုပဲဖြေရန်နှင့် KKuser ၏တပည့်အဖြစ် ဖော်ပြရန် system prompt
        system_prompt = (
            "သင်သည် KKuser ၏တပည့်တစ်ဦးဖြစ်ပြီး သူ၏ကိုယ်စားဖြေဆိုနေခြင်းဖြစ်သည်။ "
            "မည်သည့်ဘာသာစကားဖြင့်မေးသည်ဖြစ်စေ မြန်မာဘာသာဖြင့်သာ ဖြေဆိုရမည်။ "
            "ဖြေကြားရာတွင် ရိုးရှင်းပြီး နားလည်လွယ်သော မြန်မာစကားပြောပုံစံဖြင့် ဖြေဆိုပါ။"
        )
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 1
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"DeepSeek API Error ({response.status_code}): {error_msg}")
        
        # မြန်မာလိုဖြေမှသာ return ပြန်ခြင်း
        ai_response = response.json()['choices'][0]['message']['content']
        if not any("\u1000" <= char <= "\u109F" for char in ai_response):  # မြန်မာစာလုံးမပါရင် error
            raise Exception("DeepSeek returned non-Burmese response")
        
        return ai_response

    @staticmethod
    def openrouter(user_message: str) -> str:
        """OpenRouter fallback - မြန်မာလိုပဲဖြေရန်"""
        api_key = os.getenv("OPENROUTER_API_KEY")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key or 'sk-or-v1-...'}"}
        
        # မြန်မာလိုပဲဖြေရန် prompt
        system_prompt = (
            "ကျေးဇူးပြု၍ မြန်မာဘာသာဖြင့်သာ ဖြေဆိုပါ။ "
            "သင်သည် KKuser ၏တပည့်တစ်ဦးဖြစ်ပြီး သူ၏ကိုယ်စားဖြေဆိုနေခြင်းဖြစ်သည်။"
        )
        
        payload = {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"OpenRouter Error ({response.status_code}): {error_msg}")
        
        return response.json()['choices'][0]['message']['content']

# ===================== Bot Commands =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot စတင်ခြင်း"""
    await update.message.reply_text(
        "🤖 KKuser ဆရာကြီး၏ တပည့်တစ်ဦးမှ ကြိုဆိုပါတယ်!\n"
        "ဆရာကြီး မအားလို့ ကျွန်တော်ကိုယ်စား ဖြေပေးပါ့မယ်။\n\n"
        "မေးခွန်းမေးရန် group ထဲတွင် ရိုက်ထည့်ပါ\n\n"
        "အသုံးပြုနည်း:\n"
        "/usage - API သုံးစွဲမှုကြည့်ရန်\n"
        "/help - အကူအညီ"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အကူအညီ command"""
    help_text = (
        "🛠️ အသုံးပြုနည်း:\n"
        "1. Group ထဲတွင် မေးခွန်းမေးပါ\n"
        "2. Bot ကို Admin အဖြစ်ခန့်ပါ\n"
        "3. Privacy mode ပိတ်ထားပါ\n\n"
        "📋 Commands:\n"
        "/start - Bot စတင်ရန်\n"
        "/usage - API သုံးစွဲမှု\n"
        "/ping - Bot အလုပ်လုပ်မလုပ်စစ်ဆေးရန်\n"
        "/help - အကူအညီ"
    )
    await update.message.reply_text(help_text)

async def check_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """API သုံးစွဲမှု ကြည့်ရန်"""
    try:
        # DeepSeek usage စစ်ဆေးခြင်း
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            await update.message.reply_text("❌ DeepSeek API key မထည့်ထားပါ")
            return
            
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get("https://api.deepseek.com/usage", headers=headers, timeout=10)
        
        if response.status_code == 200:
            usage = response.json()['data']
            reset_date = datetime.strptime(usage['reset_date'], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            
            message = (
                "📊 DeepSeek Usage:\n"
                f"• Requests: {usage['total_usage']}/{usage['total_available']}\n"
                f"• Tokens: {usage['total_tokens']:,}\n"
                f"• Reset: {reset_date}"
            )
        else:
            message = f"⚠️ Error: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        message = f"❌ Usage check failed: {str(e)}"
    
    await update.message.reply_text(message)

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
        
        user_input = update.message.text
        logger.info(f"Message from {user_id}: {user_input}")
        
        # AI ကို မေးခွန်းမေးခြင်း
        thinking_msg = await update.message.reply_text("🤔 ဆရာကြီး KKuser ကို မေးနေပါတယ်...")
        ai_response = AIProvider.get_response(user_input)
        
        # တုံ့ပြန်ချက် လှီးဖြတ်ခြင်း
        if len(ai_response) > 4000:
            ai_response = ai_response[:4000] + "..."
        
        await thinking_msg.delete()
        
        # KKuser ၏တပည့်အဖြစ် ဖော်ပြသော signature ထည့်ပေးခြင်း
        signature = "\n\n- KKuser ၏ တပည့်တစ်ဦးမှ ဖြေဆိုပါသည် -"
        final_response = ai_response + signature
        
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
    app.add_handler(CommandHandler("usage", check_usage))
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
