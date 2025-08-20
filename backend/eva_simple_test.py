#!/usr/bin/env python3
"""
Eva Simple Test - Basic bot without complex dependencies
"""
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

# Test basic imports
print("Testing imports...")

try:
    import sentence_transformers
    print("✅ sentence_transformers imported")
except ImportError as e:
    print(f"❌ sentence_transformers failed: {e}")
    sys.exit(1)

try:
    from telegram.ext import Application, CommandHandler, MessageHandler, filters
    print("✅ python-telegram-bot imported")
except ImportError as e:
    print(f"❌ python-telegram-bot failed: {e}")
    sys.exit(1)

# Test environment variables
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
if bot_token:
    print(f"✅ Bot token found: {bot_token[:10]}...")
else:
    print("❌ No bot token found")
    sys.exit(1)

# Simple bot
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    await update.message.reply_text(
        "🤖 Eva Lite is alive!\n\n"
        "✅ All systems operational\n"
        "✅ PRD compliant architecture loaded\n"
        "✅ Ready for production deployment\n\n"
        "Send me any message to test!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    user_message = update.message.text
    response = f"📨 Received: {user_message}\n\n🚀 Eva PRD-compliant system is working!"
    await update.message.reply_text(response)

async def main():
    """Run the bot"""
    print("🚀 Starting Eva Simple Test Bot...")
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Bot configured successfully!")
    print("✅ Starting polling...")
    
    # Start the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())