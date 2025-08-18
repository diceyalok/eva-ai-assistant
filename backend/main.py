import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio
import redis.asyncio as aioredis
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from utils.logging import setup_logging
from utils.rate_limit import RateLimiter
from utils.cost_guard import CostGuard
from routing import setup_handlers

load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize Sentry if DSN is provided
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn and sentry_dsn.startswith(("http://", "https://")):
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development")
    )

# Global variables
telegram_app = None
redis_client = None
rate_limiter = None
cost_guard = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global telegram_app, redis_client, rate_limiter, cost_guard
    
    # Startup
    logger.info("Starting Eva Lite API...")
    
    # Initialize Redis
    redis_client = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"),
        decode_responses=True
    )
    
    # Initialize rate limiter and cost guard
    rate_limiter = RateLimiter(redis_client)
    cost_guard = CostGuard(redis_client)
    
    # Initialize Telegram bot
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if bot_token:
        telegram_app = Application.builder().token(bot_token).build()
        
        # Setup handlers
        setup_handlers(telegram_app, redis_client, rate_limiter, cost_guard)
        
        # Initialize the application
        await telegram_app.initialize()
        await telegram_app.start()
        
        logger.info("Telegram bot initialized successfully")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not found in environment")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Eva Lite API...")
    
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    
    if redis_client:
        await redis_client.close()

# Initialize FastAPI app
app = FastAPI(
    title="Eva Lite API",
    description="Telegram-based AI Assistant with Memory and Voice Processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Eva Lite API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    health_status = {
        "api": "healthy",
        "redis": "unknown",
        "telegram": "unknown"
    }
    
    # Check Redis connection
    try:
        if redis_client:
            await redis_client.ping()
            health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
    
    # Check Telegram bot
    if telegram_app:
        health_status["telegram"] = "healthy"
    
    return health_status

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint"""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    # Verify webhook secret
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if webhook_secret:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != webhook_secret:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    try:
        # Get update data
        update_data = await request.json()
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Process update
        await telegram_app.process_update(update)
        
        return {"ok": True}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    # TODO: Implement Prometheus metrics
    return {"message": "Metrics endpoint - TODO"}

@app.post("/set-webhook")
async def set_webhook():
    """Set Telegram webhook"""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
    webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    
    if not webhook_url:
        raise HTTPException(status_code=400, detail="TELEGRAM_WEBHOOK_URL not configured")
    
    try:
        await telegram_app.bot.set_webhook(
            url=webhook_url,
            secret_token=webhook_secret,
            allowed_updates=["message", "inline_query", "callback_query"]
        )
        
        return {"message": "Webhook set successfully", "url": webhook_url}
    
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )