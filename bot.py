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
USER_PROMPTS = {}  # {user_id: custom_prompt}
USER_PROVIDER = {}  # {user_id: 'deepseek'/'gemini'}
USER_HISTORY = {}  # {user_id: [messages]}
USER_COOLDOWN = {}  # {user_id: last_request_time}

# Configuration
REQUEST_COOLDOWN = 15  # seconds
MAX_HISTORY = 25  # Max conversation history to retain
DEFAULT_SYSTEM_PROMPT = "သင်သည် အကူအညီပေးသော AI ဖြစ်ပါသည်။ မြန်မာလို ရှင်းရှင်းလင်းလင်း ဖြေဆိုပါ။"

class AIProvider:
    @staticmethod
    def get_response(provider: str, messages: list, user_id: int) -> str:
        """Get response from selected provider with context"""
        try:
            if provider == 'deepseek':
                return AIProvider.deepseek(messages)
            elif provider == 'gemini':
                return AIProvider.gemini(messages, user_id)
            else:
                raise ValueError("Invalid provider selected")
        except Exception as e:
            logger.error(f"{provider} failed: {str(e)}")
            # Try fallback to other provider
            fallback = 'gemini' if provider == 'deepseek' else 'deepseek'
            try:
                return AIProvider.get_response(fallback, messages, user_id)
            except:
                raise Exception("All providers failed")

    @staticmethod
    def deepseek(messages: list) -> str:
        """DeepSeek API with context"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DeepSeek API key not set")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"DeepSeek API Error ({response.status_code}): {error_msg}")
        
        return response.json()['choices'][0]['message']['content']

    @staticmethod
    def gemini(messages: list, user_id: int) -> str:
        """Gemini API with context"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Gemini API key not set")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        # Get user's custom prompt or use default
        system_prompt = USER_PROMPTS.get(user_id, DEFAULT_SYSTEM_PROMPT)
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                continue  # Gemini uses separate system instruction
            contents.append({
                "parts": [{"text": msg['content']}],
                "role": "user" if msg['role'] == 'user' else "model"
            })
        
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"Gemini API Error ({response.status_code}): {error_msg}")
        
        return response.json()['candidates'][0]['content']['parts'][0]['text']

# ===================== User Data Management =====================
def get_user_history(user_id: int) -> list:
    """Get conversation history with system prompt"""
    history = USER_HISTORY.get(user_id, [])
    
    # Add system prompt if not exists
    if not any(msg['role'] == 'system' for msg in history):
        system_prompt = USER_PROMPTS.get(user_id, DEFAULT_SYSTEM_PROMPT)
        history.insert(0, {
            "role": "system",
            "content": system_prompt
        })
    
    return history[-MAX_HISTORY:]  # Return last N messages

def save_to_history(user_id: int, role: str, content: str):
    """Save message to conversation history"""
    if user_id not in USER_HISTORY:
        USER_HISTORY[user_id] = []
    
    USER_HISTORY[user_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Trim history if too long
    if len(USER_HISTORY[user_id]) > MAX_HISTORY:
        USER_HISTORY[user_id] = USER_HISTORY[user_id][-MAX_HISTORY:]

def clear_history(user_id: int):
    """Clear conversation history"""
    if user_id in USER_HISTORY:
        del USER_HISTORY[user_id]

# ===================== Bot Commands =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot စတင်ခြင်း"""
    user_id = update.message.from_user.id
    USER_PROVIDER[user_id] = 'gemini'  # Default to Gemini for better Myanmar
    
    welcome_msg = (
        "🤖 AI Assistant Bot မှ ကြိုဆိုပါတယ်!\n\n"
        "🌟 အောက်ပါ commands များဖြင့် အသုံးပြုနိုင်ပါသည်:\n"
        "/setprompt <prompt> - AI စရိုက်ပြောင်းရန်\n"
        "/myprompt - လက်ရှိ prompt ကြည့်ရန်\n"
        "/resetprompt - မူလ prompt ပြန်သုံးရန်\n"
        "/setprovider <gemini/deepseek> - AI ပြောင်းရန်\n"
        "/clearhistory - စကားဝိုင်းရှင်းရန်\n"
        "/help - အကူအညီ"
    )
    
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အကူအညီ command"""
    help_text = (
        "🛠️ အသုံးပြုနည်း:\n"
        "1. ဘာသာစကားမရွေး မေးမြန်းနိုင်ပါသည်\n"
        "2. AI က မြန်မာလို/အင်္ဂလိပ်လို အလိုအလျောက်ဖြေပါမည်\n\n"
        "📋 Commands:\n"
        "/setprompt - AI စရိုက်ပြောင်းရန် (ဥပမာ: သင်သည် ကဗျာဆရာတစ်ဦးဖြစ်သည်)\n"
        "/myprompt - လက်ရှိ prompt ကြည့်ရန်\n"
        "/setprovider - AI ပြောင်းရန် (gemini/deepseek)\n"
        "/clearhistory - စကားဝိုင်းရှင်းရန်\n"
        "/help - အကူအညီ"
    )
    await update.message.reply_text(help_text)

async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set custom AI prompt"""
    user_id = update.message.from_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Prompt မထည့်ပါ!\n\n"
            "📝 ဥပမာ:\n"
            "/setprompt သင်သည် ကဗျာဆရာတစ်ဦးဖြစ်သည်\n"
            "/setprompt You are a helpful English tutor\n"
            "/setprompt သင်သည် ရယ်စရာကောင်းသော သူငယ်ချင်းတစ်ဦးဖြစ်သည်"
        )
        return
    
    new_prompt = ' '.join(args)
    USER_PROMPTS[user_id] = new_prompt
    
    # Update system message in history
    history = get_user_history(user_id)
    if history and history[0]['role'] == 'system':
        history[0]['content'] = new_prompt
    
    await update.message.reply_text(
        f"✅ AI Prompt ပြောင်းပြီးပါပြီ!\n\n"
        f"သင့်ရဲ့ AI က ယခုအခါ:\n{new_prompt}"
    )

async def my_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current AI prompt"""
    user_id = update.message.from_user.id
    current_prompt = USER_PROMPTS.get(user_id, DEFAULT_SYSTEM_PROMPT)
    
    await update.message.reply_text(
        f"📝 လက်ရှိ AI Prompt:\n\n{current_prompt}\n\n"
        f"🔄 ပြောင်းလဲရန်: /setprompt <new_prompt>"
    )

async def reset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset to default prompt"""
    user_id = update.message.from_user.id
    if user_id in USER_PROMPTS:
        del USER_PROMPTS[user_id]
    
    # Update system message in history
    history = get_user_history(user_id)
    if history and history[0]['role'] == 'system':
        history[0]['content'] = DEFAULT_SYSTEM_PROMPT
    
    await update.message.reply_text(
        f"🔄 Prompt ကို မူလအတိုင်း ပြန်လည်သတ်မှတ်ပြီးပါပြီ!\n\n"
        f"{DEFAULT_SYSTEM_PROMPT}"
    )

async def set_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set AI provider"""
    user_id = update.message.from_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "ကျေးဇူးပြု၍ provider အမျိုးအစားထည့်ပါ။\n"
            "ဥပမာ:\n"
            "/setprovider gemini\n"
            "/setprovider deepseek"
        )
        return
    
    provider = args[0].lower()
    valid_providers = ['gemini', 'deepseek']
    
    if provider in valid_providers:
        USER_PROVIDER[user_id] = provider
        await update.message.reply_text(f"✅ AI provider ကို {provider} အဖြစ်ပြောင်းလိုက်ပါပြီ!")
    else:
        await update.message.reply_text(
            f"❌ {provider} သည် မရှိသော provider ဖြစ်ပါသည်။\n"
            f"ရနိုင်သော provider များ: {', '.join(valid_providers)}"
        )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.message.from_user.id
    clear_history(user_id)
    await update.message.reply_text("🧹 စကားဝိုင်း မှတ်တမ်း ရှင်းလင်းပြီးပါပြီ!")

# ===================== Message Handling =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages with context"""
    try:
        user_id = update.message.from_user.id
        current_time = time.time()
        
        # Check cooldown
        if user_id in USER_COOLDOWN:
            elapsed = current_time - USER_COOLDOWN[user_id]
            if elapsed < REQUEST_COOLDOWN:
                await update.message.reply_text(
                    f"⏳ ကျေးဇူးပြု၍ {REQUEST_COOLDOWN - int(elapsed)} စက္ကန့်စောင့်ပါ"
                )
                return
        
        USER_COOLDOWN[user_id] = current_time
        
        # Get user message
        user_message = update.message.text
        if not user_message or user_message.startswith('/'):
            return
        
        # Get or set default provider
        provider = USER_PROVIDER.get(user_id, 'gemini')
        
        # Prepare conversation context
        history = get_user_history(user_id)
        messages = history.copy()
        messages.append({"role": "user", "content": user_message})
        
        # Get AI response
        thinking_msg = await update.message.reply_text("🤔 တွေးဆနေပါသည်...")
        
        try:
            ai_response = AIProvider.get_response(provider, messages, user_id)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            ai_response = "⚠️ တောင်းပန်ပါသည်၊ အဖြေရယူရာတွင် ပြဿနာတစ်ခုဖြစ်နေပါသည်။ နောက်မှထပ်ကြိုးစားပါ။"
        
        # Save conversation
        save_to_history(user_id, "user", user_message)
        save_to_history(user_id, "assistant", ai_response)
        
        # Send response
        await thinking_msg.delete()
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        await update.message.reply_text("⚠️ အမှားတစ်ခုဖြစ်နေပါသည်။ ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားပါ။")

# ===================== Main Application =====================
def main():
    # Check environment variables
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        exit(1)
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setprompt", set_prompt))
    app.add_handler(CommandHandler("myprompt", my_prompt))
    app.add_handler(CommandHandler("resetprompt", reset_prompt))
    app.add_handler(CommandHandler("setprovider", set_provider))
    app.add_handler(CommandHandler("clearhistory", clear_history))
    
    # Message handler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Start bot
    logger.info("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
