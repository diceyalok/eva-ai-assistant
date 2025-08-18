# 🚀 Eva AI Assistant - Quick Start Guide

## Prerequisites

- **Docker & Docker Compose** installed
- **Domain name** (for production webhook)
- **API Keys**: OpenAI, Telegram Bot Token
- **Server**: 4GB RAM, 2+ CPU cores recommended

## 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### Required Environment Variables:
```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_WEBHOOK_URL=https://yourdomain.com
TELEGRAM_WEBHOOK_SECRET=random_secret_string

# OpenAI (for premium features)
OPENAI_API_KEY=your_openai_api_key

# Database
POSTGRES_PASSWORD=secure_random_password

# Domain (for Caddy)
DOMAIN=yourdomain.com
```

## 2. Download Models (Optional)

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Download AI models
./scripts/download_models.sh
```

## 3. Deploy Services

```bash
# Full deployment
./scripts/deploy.sh
```

## 4. Verify Deployment

```bash
# Check all services
docker-compose ps

# Check logs
docker-compose logs -f eva-api

# Test health endpoint
curl http://localhost:8000/health
```

## 5. Test Telegram Bot

1. **Find your bot** on Telegram (@your_bot_name)
2. **Send `/start`** to initialize
3. **Try commands**:
   - `/ask What is AI?`
   - `/tone friendly`
   - Send voice message
   - `/dream` (after some conversation)

## 🎯 Production Checklist

### Security
- [ ] Change default passwords
- [ ] Enable Caddy auth for admin endpoints  
- [ ] Configure firewall (ports 80, 443 only)
- [ ] Set up SSL certificates (auto with Caddy)

### Performance
- [ ] Enable GPU for vLLM (uncomment in docker-compose.yml)
- [ ] Add voice samples for TTS (./data/models/speakers/)
- [ ] Configure resource limits
- [ ] Set up monitoring

### Reliability
- [ ] Configure backup for databases
- [ ] Set up log rotation
- [ ] Configure health check monitoring
- [ ] Set up alerts (Sentry recommended)

## 🛠️ Common Commands

```bash
# View logs
docker-compose logs -f eva-api
docker-compose logs -f vllm

# Restart services
docker-compose restart eva-api
docker-compose restart

# Update deployment
git pull
docker-compose build eva-api
docker-compose up -d

# Backup data
docker-compose exec postgres pg_dump -U eva eva_db > backup.sql

# Reset everything
docker-compose down -v
docker-compose up -d
```

## 📊 Monitoring URLs

- **API Health**: `http://localhost:8000/health`
- **ChromaDB**: `http://localhost:8001`
- **vLLM API**: `http://localhost:8002/v1/models`
- **Redis**: `redis://localhost:6379`

## 🔧 Troubleshooting

### Bot not responding?
1. Check webhook: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
2. Check logs: `docker-compose logs eva-api`
3. Verify environment variables

### vLLM issues?
1. Check memory usage: `docker stats`
2. Enable CPU-only mode in .env: `USE_GPU=false`
3. Try smaller model: `VLLM_MODEL_NAME=microsoft/DialoGPT-small`

### Voice issues?
1. TTS will fallback to simple synthesis
2. Add proper voice samples to speakers folder
3. Install espeak: `apt-get install espeak`

## 📈 Performance Targets

- **Text Response**: <2.5s (local), <5s (GPT-4o)
- **Voice Processing**: <1.2s end-to-end
- **Memory Queries**: <100ms
- **Cost per User**: <₹4/month

## 🎉 Success!

Your Eva AI Assistant is now running! 

- **Telegram**: Chat with your bot
- **Voice**: Send voice messages  
- **Memory**: Bot remembers conversations
- **Personality**: Switch tones with `/tone`
- **Dreams**: Get insights with `/dream`

---

**Need help?** Check logs with `docker-compose logs -f` or create an issue in the repository.