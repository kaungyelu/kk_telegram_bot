import os
import json
import logging
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

# Configuration
JSON_DB = "user_data.json"
MAX_HISTORY = 15  # Keep last 15 messages
DEFAULT_SYSTEM_PROMPT = "မြန်မာလို ရှင်းရှင်းလင်းလင်း ဖြေဆိုပါ။ ဖော်ရွေစွာနှင့် အပြည့်အစုံဖြေပါ။"

# Initialize JSON database
def init_db():
    if not os.path.exists(JSON_DB):
        with open(JSON_DB, "w") as f:
            json.dump({
                "user_providers": {},
                "user_prompts": {},
                "conversation_history": {}
            }, f)

init_db()

# Database helper functions
def read_db():
    with open(JSON_DB, "r") as f:
        return json.load(f)

def write_db(data):
    with open(JSON_DB, "w") as f:
        json.dump(data, f, indent=2)

def get_user_data(user_id, key):
    db = read_db()
    return db[key].get(str(user_id))

def set_user_data(user_id, key, value):
    db = read_db()
    db[key][str(user_id)] = value
    write_db(db)

# AI Providers
class AIProvider:
    @staticmethod
    def get_response(provider, messages, user_id):
        try:
            if provider == 'gemini':
                return AIProvider.gemini(messages, user_id)
            elif provider == 'deepseek':
                return AIProvider.deepseek(messages)
            elif provider == 'openrouter':
                return AIProvider.openrouter(messages)
        except Exception as e:
            logger.error(f"{provider} error: {str(e)}")
            raise Exception(f"⚠️ {provider} အလုပ်မလုပ်ပါ။ ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားပါ")

    @staticmethod
    def gemini(messages, user_id):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY မရှိပါ")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        # Get user's custom prompt
        prompt = get_user_data(user_id, "user_prompts") or DEFAULT_SYSTEM_PROMPT
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                continue
            contents.append({
                "parts": [{"text": msg['content']}],
                "role": "user" if msg['role'] == 'user' else "model"
            })
        
        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": prompt}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code != 200:
            error = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"Gemini Error: {error}")
        
        return response.json()['candidates'][0]['content']['parts'][0]['text']

    @staticmethod
    def deepseek(messages):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DEEPSEEK_API_KEY မရှိပါ")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            error = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"DeepSeek Error: {error}")
        
        return response.json()['choices'][0]['message']['content']

    @staticmethod
    def openrouter(messages):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise Exception("OPENROUTER_API_KEY မရှိပါ")
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/yourusername/yourrepo",
            "X-Title": "My AI Bot"
        }
        
        payload = {
            "model": "google/gemini-pro",  # Use Gemini via OpenRouter
            "messages": messages
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            error = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"OpenRouter Error: {error}")
        
        return response.json()['choices'][0]['message']['content']

# Conversation history management
def get_history(user_id):
    history = get_user_data(user_id, "conversation_history") or []
    
    # Add system prompt if not exists
    if not any(msg['role'] == 'system' for msg in history):
        prompt = get_user_data(user_id, "user_prompts") or DEFAULT_SYSTEM_PROMPT
        history.insert(0, {"role": "system", "content": prompt})
    
    return history[-MAX_HISTORY:]

def save_to_history(user_id, role, content):
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    set_user_data(user_id, "conversation_history", history[-MAX_HISTORY:])

def clear_history(user_id):
    set_user_data(user_id, "conversation_history", [])

# Telegram Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    set_user_data(user_id, "user_providers", "gemini")  # Default to Gemini
    
    await update.message.reply_text(
        "🤖 AI Assistant Bot မှ ကြိုဆိုပါတယ်!\n\n"
        "✨ အသုံးပြုနည်း:\n"
        "/setprompt <prompt> - AI စရိုက်ပြောင်းရန်\n"
        "/setprovider <gemini/deepseek/openrouter> - AI ပြောင်းရန်\n"
        "/clearhistory - စကားဝိုင်းရှင်းရန်\n"
        "/help - အကူအညီ"
    )

async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text(
            "❌ Prompt မထည့်ပါ!\nဥပမာ:\n"
            "/setprompt သင်သည် ကဗျာဆရာတစ်ဦးဖြစ်သည်\n"
            "/setprompt You are an English tutor"
        )
        return
    
    new_prompt = ' '.join(context.args)
    set_user_data(user_id, "user_prompts", new_prompt)
    
    # Update system message in history
    history = get_history(user_id)
    if history and history[0]['role'] == 'system':
        history[0]['content'] = new_prompt
        set_user_data(user_id, "conversation_history", history)
    
    await update.message.reply_text(f"✅ Prompt ပြောင်းပြီးပါပြီ:\n{new_prompt}")

async def set_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text(
            "❌ Provider မထည့်ပါ!\nဥပမာ:\n"
            "/setprovider gemini\n"
            "/setprovider deepseek\n"
            "/setprovider openrouter"
        )
        return
    
    provider = context.args[0].lower()
    if provider not in ['gemini', 'deepseek', 'openrouter']:
        await update.message.reply_text("❌ မသိသော provider! gemini/deepseek/openrouter သာရွေးပါ")
        return
    
    set_user_data(user_id, "user_providers", provider)
    await update.message.reply_text(f"✅ AI provider ကို {provider} အဖြစ်ပြောင်းပြီးပါပြီ!")

async def clear_history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    clear_history(user_id)
    await update.message.reply_text("🧹 စကားဝိုင်းမှတ်တမ်း ရှင်းလင်းပြီးပါပြီ")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠️ အသုံးပြုနည်း:\n"
        "1. ဘာသာစကားမရွေး မေးမြန်းနိုင်ပါသည်\n"
        "2. AI က မြန်မာ/အင်္ဂလိပ်လို အလိုအလျောက်ဖြေပါမည်\n\n"
        "📋 Commands:\n"
        "/setprompt - AI စရိုက်ပြောင်းရန်\n"
        "/setprovider - AI ပြောင်းရန် (gemini/deepseek/openrouter)\n"
        "/clearhistory - စကားဝိုင်းရှင်းရန်\n"
        "/help - အကူအညီ"
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text
    
    if not user_message or user_message.startswith('/'):
        return
    
    try:
        # Get user settings
        provider = get_user_data(user_id, "user_providers") or "gemini"
        history = get_history(user_id)
        
        # Add user message to history
        history.append({"role": "user", "content": user_message})
        
        # Get AI response
        thinking_msg = await update.message.reply_text("🤔 တွေးဆနေပါသည်...")
        ai_response = AIProvider.get_response(provider, history, user_id)
        
        # Save conversation
        save_to_history(user_id, "assistant", ai_response)
        
        await thinking_msg.delete()
        await update.message.reply_text(ai_response)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"⚠️ အမှားတစ်ခုဖြစ်နေပါသည်: {str(e)}")

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
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setprompt", set_prompt))
    app.add_handler(CommandHandler("setprovider", set_provider))
    app.add_handler(CommandHandler("clearhistory", clear_history_cmd))
    
    # Message handler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    # Start bot
    logger.info("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    import requests  # Required for API calls
    main()
