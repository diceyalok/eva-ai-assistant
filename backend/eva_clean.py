#!/usr/bin/env python3
"""
Eva Clean Architecture - Entry Point
Demonstrates the new clean, efficient architecture
"""
import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

# Import our clean architecture
from core import (
    model_manager, 
    config, 
    ai_service, 
    memory_service, 
    voice_service,
    telegram_gateway
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EvaCleanBot:
    """Eva bot with clean architecture"""
    
    def __init__(self):
        self.running = False
    
    async def initialize(self):
        """Initialize all services"""
        logger.info("🚀 Starting Eva Clean Architecture...")
        
        # Validate configuration first
        if not config.validate_config():
            logger.error("❌ Configuration validation failed")
            return False
        
        logger.info(f"✅ Configuration validated for {config.environment} environment")
        
        try:
            # Initialize all services in order
            logger.info("📚 Warming up models...")
            await model_manager.warm_up_models()
            
            logger.info("🤖 Initializing AI service...")
            await ai_service.initialize()
            
            logger.info("🧠 Initializing memory service...")
            await memory_service.initialize()
            
            logger.info("🎵 Initializing voice service...")
            await voice_service.initialize()
            
            logger.info("📡 Initializing Telegram gateway...")
            await telegram_gateway.initialize()
            
            logger.info("🎯 All services initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    async def start_polling(self):
        """Start in polling mode"""
        if not await self.initialize():
            return
        
        self.running = True
        logger.info("🔄 Starting Telegram polling...")
        
        try:
            await telegram_gateway.start_polling()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Received stop signal")
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
        finally:
            await self.cleanup()
    
    async def start_webhook(self):
        """Start in webhook mode"""
        if not await self.initialize():
            return
        
        self.running = True
        logger.info("🌐 Starting Telegram webhook...")
        
        try:
            await telegram_gateway.start_webhook()
            
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Received stop signal")
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
        finally:
            await self.cleanup()
    
    async def run_health_check(self):
        """Run a comprehensive health check"""
        logger.info("🏥 Running health check...")
        
        try:
            # Initialize services
            await self.initialize()
            
            # Get health from all services
            ai_health = await ai_service.get_service_status()
            memory_stats = await memory_service.get_memory_stats()
            voice_health = await voice_service.health_check()
            gateway_stats = await telegram_gateway.get_gateway_stats()
            
            print("\n" + "="*50)
            print("🏥 EVA HEALTH CHECK REPORT")
            print("="*50)
            
            print(f"\n🤖 AI SERVICE:")
            print(f"  • Initialized: {ai_health['initialized']}")
            print(f"  • Local AI: {ai_health['local_ai']}")
            print(f"  • OpenAI: {ai_health['openai']}")
            print(f"  • Models: {ai_health['models']['loaded_models']}")
            
            print(f"\n🧠 MEMORY SERVICE:")
            print(f"  • Initialized: {memory_stats['initialized']}")
            print(f"  • Collection count: {memory_stats['collection_count']}")
            print(f"  • Redis connected: {memory_stats['redis_connected']}")
            print(f"  • Embedding model: {memory_stats['embedding_model']}")
            
            print(f"\n🎵 VOICE SERVICE:")
            print(f"  • Service: {voice_health['service']}")
            print(f"  • Whisper: {voice_health['whisper']}")
            print(f"  • Redis: {voice_health['redis']}")
            print(f"  • FFmpeg: {voice_health['ffmpeg']}")
            print(f"  • Audio libs: {voice_health['audio_libs']}")
            
            print(f"\n📡 TELEGRAM GATEWAY:")
            print(f"  • Initialized: {gateway_stats['initialized']}")
            print(f"  • Webhook mode: {gateway_stats['webhook_mode']}")
            print(f"  • Bot token configured: {gateway_stats['bot_token_configured']}")
            
            print(f"\n📊 CONFIGURATION:")
            print(f"  • Environment: {config.environment}")
            print(f"  • Has OpenAI: {config.ai.has_openai}")
            print(f"  • Webhook mode: {config.telegram.is_webhook_mode}")
            print(f"  • TTS enabled: {config.voice.tts_enabled}")
            
            print("\n" + "="*50)
            print("✅ Health check completed!")
            print("="*50)
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup all services"""
        logger.info("🧹 Cleaning up services...")
        
        try:
            await telegram_gateway.stop()
            await ai_service.cleanup()
            await memory_service.cleanup()
            await voice_service.cleanup()
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
    
    def stop(self):
        """Stop the bot"""
        self.running = False

# Signal handlers
eva_bot = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global eva_bot
    logger.info(f"Received signal {signum}")
    if eva_bot:
        eva_bot.stop()

async def main():
    """Main entry point"""
    global eva_bot
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    eva_bot = EvaCleanBot()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "health":
            await eva_bot.run_health_check()
        elif command == "webhook":
            await eva_bot.start_webhook()
        elif command == "polling":
            await eva_bot.start_polling()
        else:
            print("Usage: python eva_clean.py [health|webhook|polling]")
            print("  health  - Run health check")
            print("  webhook - Start in webhook mode")
            print("  polling - Start in polling mode (default)")
    else:
        # Default to polling mode
        await eva_bot.start_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Eva Clean Architecture stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)