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
USER_PROVIDER = {}  # {user_id: 'deepseek'/'gemini'}
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
            else:
                raise ValueError("Invalid provider selected")
        except Exception as e:
            logger.error(f"{provider} failed: {str(e)}")
            # Try fallback to the other provider
            fallback = 'gemini' if provider == 'deepseek' else 'deepseek'
            try:
                return AIProvider.fallback(fallback, user_message)
            except Exception as e:
                logger.error(f"Fallback {fallback} failed: {str(e)}")
                raise Exception("Both providers failed")

    @staticmethod
    def deepseek(user_message: str) -> str:
        """DeepSeek API - responds in user's language as KKuser's student"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DeepSeek API key not set")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # System prompt in English (applies to all languages)
        system_prompt = (
            "You are a student of KKuser answering on his behalf. "
            "Respond in the SAME LANGUAGE as the user's question. "
            "Keep your answers concise and helpful."
        )
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"DeepSeek API Error ({response.status_code}): {error_msg}")
        
        return response.json()['choices'][0]['message']['content']

    @staticmethod
    def gemini(user_message: str) -> str:
        """Gemini 2.5 API - responds in user's language as KKuser's student"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Gemini API key not set")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
        
        # System instruction in English (applies to all languages)
        system_instruction = (
            "You are a student of KKuser answering on his behalf. "
            "Respond in the SAME LANGUAGE as the user's question. "
            "Keep answers concise and to the point."
        )
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_instruction},
                        {"text": user_message}
                    ]
                }
            ],
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

    @staticmethod
    def fallback(provider: str, user_message: str) -> str:
        """Fallback to another provider"""
        if provider == 'deepseek':
            return AIProvider.deepseek(user_message)
        elif provider == 'gemini':
            return AIProvider.gemini(user_message)
        else:
            raise ValueError("Invalid fallback provider")

# ===================== Bot Commands =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot စတင်ခြင်း"""
    user_id = update.message.from_user.id
    USER_PROVIDER[user_id] = 'deepseek'  # Default provider
    
    await update.message.reply_text(
        "🤖 KKuser's Assistant Bot\n\n"
        "I'm KKuser's student answering on his behalf\n"
        "Ask anything in this chat!\n\n"
        "Commands:\n"
        "/setprovider - Change AI provider (deepseek/gemini)\n"
        "/getprovider - Show current provider\n"
        "/help - Show help"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """အကူအညီ command"""
    help_text = (
        "🛠️ How to use:\n"
        "1. Use /setprovider to choose AI\n"
        "2. Ask any question in chat\n\n"
        "📋 Commands:\n"
        "/start - Start bot\n"
        "/setprovider - Change AI provider\n"
        "/getprovider - Show current provider\n"
        "/ping - Check bot status\n"
        "/help - Show help"
    )
    await update.message.reply_text(help_text)

async def set_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set AI provider"""
    user_id = update.message.from_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Please specify provider:\n"
            "/setprovider deepseek\n"
            "/setprovider gemini"
        )
        return
    
    provider = args[0].lower()
    valid_providers = ['deepseek', 'gemini']
    
    if provider in valid_providers:
        USER_PROVIDER[user_id] = provider
        await update.message.reply_text(f"✅ Set AI provider to: {provider}")
    else:
        await update.message.reply_text(
            f"❌ Invalid provider: {provider}\n"
            f"Available: {', '.join(valid_providers)}"
        )

async def get_provider(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current AI provider"""
    user_id = update.message.from_user.id
    provider = USER_PROVIDER.get(user_id, 'deepseek')
    await update.message.reply_text(f"🔧 Current AI provider: {provider}")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot အလုပ်လုပ်မလုပ် စစ်ဆေးခြင်း"""
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pong!...")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"🏓 Pong! Latency: {latency}ms")

# ===================== Message Handling =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in groups"""
    try:
        user_id = update.message.from_user.id
        current_time = time.time()
        
        # Cooldown check
        if user_id in USER_COOLDOWN:
            elapsed = current_time - USER_COOLDOWN[user_id]
            if elapsed < REQUEST_COOLDOWN:
                await update.message.reply_text(
                    f"⏳ Please wait {REQUEST_COOLDOWN - int(elapsed)} seconds"
                )
                return
        
        USER_COOLDOWN[user_id] = current_time
        
        # Get or set default provider
        provider = USER_PROVIDER.get(user_id, 'deepseek')
        user_input = update.message.text
        
        # Get AI response
        thinking_msg = await update.message.reply_text(f"🤔 Asking KKuser via {provider}...")
        
        try:
            ai_response = AIProvider.get_response(provider, user_input)
        except Exception as e:
            logger.error(f"All providers failed: {str(e)}")
            ai_response = "⚠️ Sorry, all AI providers are unavailable. Please try again later."
        
        # Add signature
        final_response = f"{ai_response}\n\n- Answered by KKuser's student -"
        
        if len(final_response) > 4000:
            final_response = final_response[:4000] + "..."
        
        await thinking_msg.delete()
        await update.message.reply_text(final_response)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        error_msg = (
            "⚠️ Error processing request\n"
            "Please try again later"
        )
        await update.message.reply_text(error_msg)

# ===================== Main Application =====================
def main():
    # Check bot token
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN environment variable not set!")
        exit(1)
    
    # Create bot application
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
    
    # Start bot
    logger.info("🤖 KKuser Assistant Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
