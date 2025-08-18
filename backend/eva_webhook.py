#!/usr/bin/env python3
"""
Eva Webhook Mode - Optimized for RunPod
High-performance webhook mode with GPU acceleration
"""

import asyncio
import logging
import os
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import json

# Eva components
from core.config_manager import config
from core.model_manager import model_manager
from core.ai_service import ai_service
from core.memory_service import memory_service
from core.voice_service import voice_service
from core.telegram_gateway import telegram_gateway

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Eva Telegram Bot",
    description="High-performance AI assistant with GPU acceleration",
    version="2.0.0"
)

# Global state
services_initialized = False
telegram_app = None

async def initialize_services():
    """Initialize all Eva services"""
    global services_initialized
    
    if services_initialized:
        return
    
    logger.info("🚀 Initializing Eva services for webhook mode...")
    
    try:
        # Validate configuration
        if not config.telegram.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        
        # Warm up models (critical for performance)
        logger.info("🔥 Warming up GPU models...")
        await model_manager.warmup_models()
        
        # Initialize services
        logger.info("🤖 Initializing AI service...")
        await ai_service.initialize()
        
        logger.info("🧠 Initializing memory service...")
        await memory_service.initialize()
        
        logger.info("🎵 Initializing voice service...")
        await voice_service.initialize()
        
        logger.info("📡 Initializing Telegram gateway...")
        await telegram_gateway.initialize()
        
        services_initialized = True
        logger.info("✅ All Eva services initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """FastAPI startup event"""
    await initialize_services()

@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event"""
    logger.info("🛑 Shutting down Eva services...")
    
    try:
        await ai_service.cleanup()
        await memory_service.cleanup()
        await voice_service.cleanup()
        logger.info("✅ Eva services shut down successfully")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint for RunPod"""
    if not services_initialized:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    # Check service health
    ai_status = await ai_service.get_service_status()
    memory_stats = await memory_service.get_memory_stats()
    
    return {
        "status": "healthy",
        "services": {
            "ai": ai_status.get("initialized", False),
            "memory": memory_stats.get("initialized", False),
            "voice": True,  # Voice service doesn't have status check
            "telegram": services_initialized
        },
        "gpu_available": os.getenv("CUDA_VISIBLE_DEVICES") is not None,
        "version": "2.0.0"
    }

@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    if not services_initialized:
        return {"error": "Services not initialized"}
    
    try:
        memory_stats = await memory_service.get_memory_stats()
        ai_status = await ai_service.get_service_status()
        
        return {
            "memory": memory_stats,
            "ai": ai_status,
            "uptime": "webhook_mode",
            "gpu_memory": get_gpu_memory_usage()
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {"error": str(e)}

def get_gpu_memory_usage():
    """Get GPU memory usage if available"""
    try:
        import torch
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated(0)
            memory_reserved = torch.cuda.memory_reserved(0)
            return {
                "allocated_mb": memory_allocated / 1024 / 1024,
                "reserved_mb": memory_reserved / 1024 / 1024,
                "device_count": torch.cuda.device_count()
            }
    except Exception:
        pass
    return {"gpu_available": False}

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Main webhook handler for Telegram"""
    if not services_initialized:
        raise HTTPException(status_code=503, detail="Services not ready")
    
    try:
        # Get request body
        body = await request.body()
        update_dict = json.loads(body.decode('utf-8'))
        
        # Process update through Telegram gateway
        await telegram_gateway.process_webhook_update(update_dict)
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set-webhook")
async def set_webhook():
    """Set Telegram webhook URL"""
    try:
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("WEBHOOK_URL environment variable not set")
        
        result = await telegram_gateway.set_webhook(f"{webhook_url}/webhook")
        return {"status": "success", "result": result}
        
    except Exception as e:
        logger.error(f"Set webhook error: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🚀 Starting Eva webhook server on {host}:{port}")
    
    # Run with GPU-optimized settings
    uvicorn.run(
        "eva_webhook:app",
        host=host,
        port=port,
        workers=1,  # Single worker for GPU efficiency
        access_log=True,
        log_level="info",
        loop="asyncio"
    )