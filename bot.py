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

# User cooldown
USER_COOLDOWN = {}
REQUEST_COOLDOWN = 15  # seconds

class AIProvider:
    @staticmethod
    def get_response(user_message: str) -> str:
        """Automatically switch between AI providers"""
        try:
            return AIProvider.deepseek(user_message)
        except Exception as e:
            logger.error(f"DeepSeek failed: {str(e)}")
            return AIProvider.gemini(user_message)  # Changed to Gemini fallback

    @staticmethod
    def deepseek(user_message: str) -> str:
        """DeepSeek API with dynamic language"""
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DeepSeek API key not set")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # Dynamic language response
        system_prompt = (
            "You are a student of KKuser answering on his behalf. "
            "Respond in the SAME LANGUAGE as the user's question."
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
        """Gemini 2.5 API fallback"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("Gemini API key not set")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
        
        # Dynamic language instruction
        system_instruction = (
            "You are a student of KKuser answering on his behalf. "
            "Respond in the SAME LANGUAGE as the user's question."
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

# ===================== Bot Commands =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 KKuser's assistant bot is ready!\n"
        "Ask anything in the group chat\n\n"
        "Usage:\n"
        "/usage - Check API usage\n"
        "/help - Help guide"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠️ How to use:\n"
        "1. Ask questions in group chat\n"
        "2. Make bot admin\n"
        "3. Disable privacy mode\n\n"
        "📋 Commands:\n"
        "/start - Start bot\n"
        "/usage - Check API usage\n"
        "/ping - Check bot status\n"
        "/help - Show help"
    )
    await update.message.reply_text(help_text)

async def check_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            await update.message.reply_text("❌ DeepSeek API key not configured")
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
            message = f"⚠️ Error: {response.status_code}"
    except Exception as e:
        message = f"❌ Usage check failed: {str(e)}"
    
    await update.message.reply_text(message)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Pong!...")
    end_time = time.time()
    latency = round((end_time - start_time) * 1000, 2)
    await msg.edit_text(f"🏓 Pong! Latency: {latency}ms")

# ===================== Message Handling =====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        user_input = update.message.text
        logger.info(f"Message from {user_id}: {user_input}")
        
        # Get AI response
        thinking_msg = await update.message.reply_text("🤔 Asking KKuser...")
        ai_response = AIProvider.get_response(user_input)
        
        # Add signature
        final_response = f"{ai_response}\n\n- Answered by KKuser's student"
        
        if len(final_response) > 4000:
            final_response = final_response[:4000] + "..."
        
        await thinking_msg.delete()
        await update.message.reply_text(final_response)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        error_msg = (
            "⚠️ Error getting response\n"
            "Please try again later"
        )
        await update.message.reply_text(error_msg)

# ===================== Main Application =====================
def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("TELEGRAM_TOKEN not set!")
        exit(1)
    
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
    
    logger.info("🤖 Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
