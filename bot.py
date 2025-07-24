import os
import json
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Default system prompt
DEFAULT_SYSTEM_PROMPT = "သင်သည်အကူညီပေးသော AI ဖြစ်ပါသည်။ မြန်မာလို ပြန်ကြားပါ။"

# User data storage
USER_DATA_FILE = 'user_data.json'

# Initialize user data
def load_user_data():
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

user_data = load_user_data()

# Helper functions for user data
def get_user_data(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
            'prompt': DEFAULT_SYSTEM_PROMPT,
            'history': [],
            'ai_provider': 'gemini'  # default provider
        }
    return user_data[str(user_id)]

def update_user_data(user_id, data):
    user_data[str(user_id)] = data
    save_user_data(user_data)

# AI Provider Functions
async def get_gemini_response(prompt, history, system_prompt):
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured."
    
    contents = []
    
    # Add history
    for conv in history:
        contents.append({"role": "user", "parts": [{"text": conv['user']}]})
        contents.append({"role": "model", "parts": [{"text": conv['ai']}]})
    
    # Add current message
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            if result.get('candidates') and result['candidates'][0].get('content'):
                return result['candidates'][0]['content']['parts'][0]['text']
        return "Error: Could not get response from Gemini."
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "Error connecting to Gemini service."

async def get_deepseek_response(prompt, history, system_prompt):
    if not DEEPSEEK_API_KEY:
        return "DeepSeek API key is not configured."
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history
    for conv in history:
        messages.append({"role": "user", "content": conv['user']})
        messages.append({"role": "assistant", "content": conv['ai']})
    
    # Add current message
    messages.append({"role": "user", "content": prompt})
    
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"Error: DeepSeek API returned {response.status_code}"
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Error connecting to DeepSeek service."

async def get_openrouter_response(prompt, history, system_prompt):
    if not OPENROUTER_API_KEY:
        return "OpenRouter API key is not configured."
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history
    for conv in history:
        messages.append({"role": "user", "content": conv['user']})
        messages.append({"role": "assistant", "content": conv['ai']})
    
    # Add current message
    messages.append({"role": "user", "content": prompt})
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://your-telegram-bot.com",  # Required by OpenRouter
        "X-Title": "Telegram AI Bot"  # Required by OpenRouter
    }
    
    payload = {
        "model": "anthropic/claude-3-haiku",  # You can change this to any model on OpenRouter
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"Error: OpenRouter API returned {response.status_code}"
    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        return "Error connecting to OpenRouter service."

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_msg = f"""
🤖 မင်္ဂလာပါ {user.first_name}! AI Bot မှ ကြိုဆိုပါတယ်!

🆓 လုံးဝ အခမဲ့ သုံးနိုင်ပါတယ်!

⚡ AI Commands
/setprompt <prompt> - AI ကို စိတ်ကြိုက် ပြောင်းလဲရန်
/myprompt - လက်ရှိ prompt ကြည့်ရန်
/resetprompt - မူလ prompt ပြန်သုံးရန်
/clearhistory - စကားဝိုင်း ရှင်းလင်းရန်
/setai <provider> - AI provider ပြောင်းရန် (gemini, deepseek, openrouter)
/help - အကူအညီ
"""
    await update.message.reply_text(welcome_msg)

async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        help_text = """
❌ Prompt ထည့်ပါ!

📝 Example:
/setprompt သင်သည် ကဗျာဆရာတစ်ဦးဖြစ်သည်
/setprompt You are a helpful coding assistant
/setprompt သင်သည် ရယ်စရာကောင်းသော သူငယ်ချင်းတစ်ဦးဖြစ်သည်
"""
        await update.message.reply_text(help_text)
        return
    
    new_prompt = ' '.join(args)
    user_data = get_user_data(user_id)
    user_data['prompt'] = new_prompt
    update_user_data(user_id, user_data)
    
    response = f"""
✅ AI Prompt ကို အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ!

🤖 သင့်ရဲ့ AI က ယခုအချိန်မှစ၍:
{new_prompt}

💬 စမ်းကြည့်လိုက်ပါ!
"""
    await update.message.reply_text(response)

async def my_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    response = f"""
🤖 လက်ရှိ AI Prompt

{user_data['prompt']}

🔄 ပြောင်းလဲရန်: /setprompt <new_prompt>
"""
    await update.message.reply_text(response)

async def reset_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data['prompt'] = DEFAULT_SYSTEM_PROMPT
    update_user_data(user_id, user_data)
    
    response = f"""
🔄 AI Prompt ကို မူလအတိုင်း ပြန်လည်သတ်မှတ်ပြီးပါပြီ!

🤖 Default: {DEFAULT_SYSTEM_PROMPT}
"""
    await update.message.reply_text(response)

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    user_data['history'] = []
    update_user_data(user_id, user_data)
    
    await update.message.reply_text("✅ စကားဝိုင်း မှတ်တမ်း ရှင်းလင်းပြီးပါပြီ")

async def set_ai_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        help_text = """
❌ AI provider ထည့်ပါ!

Available providers:
- gemini
- deepseek
- openrouter

Example: /setai deepseek
"""
        await update.message.reply_text(help_text)
        return
    
    provider = args[0].lower()
    if provider not in ['gemini', 'deepseek', 'openrouter']:
        await update.message.reply_text("❌ Invalid provider. Choose from: gemini, deepseek, openrouter")
        return
    
    user_data = get_user_data(user_id)
    user_data['ai_provider'] = provider
    update_user_data(user_id, user_data)
    
    await update.message.reply_text(f"✅ AI provider changed to {provider}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 AI Bot Commands

🆓 လုံးဝအခမဲ့ သုံးနိုင်ပါတယ်!

🎯 AI Customization
/setprompt <text> - AI စရိုက်ပြောင်းရန်
/myprompt - လက်ရှိ AI စရိုက်ကြည့်ရန်
/resetprompt - မူလ AI ပြန်သုံးရန်
/setai <provider> - AI provider ပြောင်းရန် (gemini, deepseek, openrouter)
/clearhistory - စကားဝိုင်းရှင်းရန်
/help - အကူအညီ
"""
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return
    
    user_data = get_user_data(user_id)
    prompt = user_data['prompt']
    history = user_data['history']
    
    # Get the appropriate AI response based on provider
    provider = user_data.get('ai_provider', 'gemini')
    
    if provider == 'gemini':
        ai_response = await get_gemini_response(text, history, prompt)
    elif provider == 'deepseek':
        ai_response = await get_deepseek_response(text, history, prompt)
    elif provider == 'openrouter':
        ai_response = await get_openrouter_response(text, history, prompt)
    else:
        ai_response = "Invalid AI provider configured"
    
    # Save conversation
    history.append({
        'user': text,
        'ai': ai_response,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep only last 25 messages
    if len(history) > 25:
        history = history[-25:]
    
    user_data['history'] = history
    update_user_data(user_id, user_data)
    
    await update.message.reply_text(ai_response)

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setprompt", set_prompt))
    application.add_handler(CommandHandler("myprompt", my_prompt))
    application.add_handler(CommandHandler("resetprompt", reset_prompt))
    application.add_handler(CommandHandler("clearhistory", clear_history))
    application.add_handler(CommandHandler("setai", set_ai_provider))
    application.add_handler(CommandHandler("help", help_command))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
