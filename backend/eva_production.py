#!/usr/bin/env python3
"""
Eva Production - Enhanced version with better error handling and monitoring
"""
import asyncio
import logging
import signal
import sys
import time
from datetime import datetime

# Import our clean architecture
from core import (
    model_manager, 
    config, 
    ai_service, 
    memory_service, 
    voice_service,
    telegram_gateway
)

# Setup enhanced logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('../logs/eva_production.log')
    ]
)
logger = logging.getLogger(__name__)

class EvaProductionBot:
    """Enhanced Eva bot with production features"""
    
    def __init__(self):
        self.running = False
        self.start_time = None
        self.stats = {
            "messages_processed": 0,
            "errors": 0,
            "uptime_start": None
        }
    
    async def initialize_with_monitoring(self):
        """Initialize with enhanced monitoring"""
        logger.info("🚀 Starting Eva Production Bot...")
        self.start_time = datetime.utcnow()
        self.stats["uptime_start"] = self.start_time
        
        # Validate configuration
        if not config.validate_config():
            logger.error("❌ Configuration validation failed")
            return False
        
        try:
            # Initialize services with timing
            start = time.time()
            
            logger.info("📚 Warming up models...")
            await model_manager.warm_up_models()
            model_time = time.time() - start
            
            logger.info("🤖 Initializing AI service...")
            await ai_service.initialize()
            
            logger.info("🧠 Initializing memory service...")
            await memory_service.initialize()
            
            logger.info("🎵 Initializing voice service...")
            await voice_service.initialize()
            
            logger.info("📡 Initializing Telegram gateway...")
            await telegram_gateway.initialize()
            
            total_time = time.time() - start
            
            logger.info(f"🎯 All services initialized in {total_time:.2f}s (models: {model_time:.2f}s)")
            
            # Print startup summary
            await self._print_startup_summary()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _print_startup_summary(self):
        """Print startup summary with health status"""
        print("\n" + "="*60)
        print("🎯 EVA PRODUCTION BOT - STARTUP SUMMARY")
        print("="*60)
        
        # Model status
        model_info = model_manager.get_model_info()
        print(f"📚 Models loaded: {len(model_info['loaded_models'])}")
        for model in model_info['loaded_models']:
            print(f"   ✅ {model}")
        
        # Service health
        ai_health = await ai_service.get_service_status()
        memory_stats = await memory_service.get_memory_stats()
        voice_health = await voice_service.health_check()
        
        print(f"\n🤖 AI Service: {'✅' if ai_health['initialized'] else '❌'}")
        print(f"   Local AI: {ai_health['local_ai']}")
        print(f"   OpenAI: {ai_health['openai']}")
        
        print(f"\n🧠 Memory Service: {'✅' if memory_stats['initialized'] else '❌'}")
        print(f"   Collections: {memory_stats['collection_count']}")
        print(f"   Redis: {'✅' if memory_stats['redis_connected'] else '❌'}")
        
        print(f"\n🎵 Voice Service: {'✅' if voice_health['service'] == 'healthy' else '❌'}")
        print(f"   Whisper: {voice_health['whisper']}")
        print(f"   FFmpeg: {voice_health['ffmpeg']}")
        
        print(f"\n📡 Environment: {config.environment}")
        print(f"🕐 Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    async def start_with_monitoring(self):
        """Start with enhanced monitoring and error recovery"""
        if not await self.initialize_with_monitoring():
            return
        
        self.running = True
        logger.info("🔄 Starting Telegram polling with monitoring...")
        
        try:
            await telegram_gateway.start_polling()
            
            # Monitor loop
            last_health_check = time.time()
            while self.running:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                # Periodic health check (every 5 minutes)
                if time.time() - last_health_check > 300:
                    await self._health_check()
                    last_health_check = time.time()
                    
        except KeyboardInterrupt:
            logger.info("⏹️ Received stop signal")
        except Exception as e:
            logger.error(f"❌ Critical error: {e}")
            self.stats["errors"] += 1
        finally:
            await self.cleanup()
    
    async def _health_check(self):
        """Periodic health check"""
        try:
            uptime = datetime.utcnow() - self.start_time
            logger.info(f"💓 Health check - Uptime: {uptime}, Messages: {self.stats['messages_processed']}, Errors: {self.stats['errors']}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def cleanup(self):
        """Enhanced cleanup with stats"""
        logger.info("🧹 Shutting down Eva Production Bot...")
        
        uptime = datetime.utcnow() - self.start_time if self.start_time else None
        
        try:
            await telegram_gateway.stop()
            await ai_service.cleanup()
            await memory_service.cleanup()
            await voice_service.cleanup()
            
            print(f"\n📊 Final Stats:")
            print(f"   Uptime: {uptime}")
            print(f"   Messages: {self.stats['messages_processed']}")
            print(f"   Errors: {self.stats['errors']}")
            
            logger.info("✅ Cleanup completed successfully")
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
    
    eva_bot = EvaProductionBot()
    await eva_bot.start_with_monitoring()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Eva Production Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)