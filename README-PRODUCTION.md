# Eva Lite - Production Ready AI Assistant

**PRD-Compliant Telegram AI Assistant with vLLM, LoRA Personalities, and XTTS v2**

[![Production Ready](https://img.shields.io/badge/Status-Production%20Ready-green)](https://github.com)
[![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)](https://github.com)
[![Performance](https://img.shields.io/badge/Performance-%E2%89%A42.5s%20text%20%7C%20%E2%89%A41.2s%20voice-orange)](https://github.com)
[![Cost](https://img.shields.io/badge/Cost-%E2%89%A4%E2%82%B920k%2Fmonth-green)](https://github.com)

## 🏗️ Architecture Overview

Eva Lite implements a complete microservices architecture designed to meet strict performance and cost requirements:

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Caddy     │────│   FastAPI    │────│    vLLM     │
│ (Reverse    │    │  (Webhook)   │    │ (Llama-3)   │
│  Proxy)     │    │              │    │   + LoRA    │
└─────────────┘    └──────────────┘    └─────────────┘
                            │
                   ┌────────▼────────┐
                   │  Support Stack  │
                   │ ChromaDB+Redis  │
                   │ XTTS + Storage  │
                   └─────────────────┘
```

### 🎯 Performance Targets (PRD Compliant)

- **Text Response**: ≤2.5 seconds
- **Voice Response**: ≤1.2 seconds  
- **Monthly Cost**: ≤₹20,000
- **Uptime**: 99.9%

## 🚀 Quick Start

### Production Deployment

```bash
# 1. Clone and configure
git clone <repository>
cd eva
cp .env.example .env
# Edit .env with your configuration

# 2. Deploy with one command
chmod +x scripts/deploy-production.sh
./scripts/deploy-production.sh

# 3. Set webhook
curl -X POST http://localhost:8000/set-webhook
```

### Development Setup

```bash
# Start development environment
chmod +x scripts/start-dev.sh
./scripts/start-dev.sh start

# Run Eva backend
./scripts/start-dev.sh run
```

## 📋 System Requirements

### Minimum Production Requirements
- **CPU**: 4 cores, 3.0GHz+
- **RAM**: 16GB
- **GPU**: NVIDIA RTX 3060 (8GB VRAM) or better
- **Storage**: 100GB SSD
- **Network**: 100Mbps bandwidth

### Recommended Production Setup
- **CPU**: 8 cores, 3.5GHz+
- **RAM**: 32GB
- **GPU**: NVIDIA RTX 4090 (24GB VRAM)
- **Storage**: 500GB NVMe SSD
- **Network**: 1Gbps bandwidth

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Core Configuration
ENVIRONMENT=production
DOMAIN=your-domain.com
TELEGRAM_BOT_TOKEN=your_bot_token

# AI Configuration  
VLLM_MODEL_NAME=meta-llama/Meta-Llama-3-8B-Instruct
OPENAI_API_KEY=your_openai_key  # Fallback

# Performance Tuning
TEXT_RESPONSE_TARGET=2.5
VOICE_RESPONSE_TARGET=1.2
GPU_MEMORY_UTILIZATION=0.8
```

### Service Configuration

#### vLLM Server
- **Model**: Llama-3 8B Instruct
- **LoRA Adapters**: 3 personality modes
- **Max Context**: 4096 tokens
- **API**: OpenAI-compatible

#### XTTS v2 
- **Engine**: Coqui XTTS v2
- **Languages**: English (optimized)
- **Voices**: 3 personality-matched speakers
- **Latency**: Streaming for <1.2s response

#### Memory System
- **Vector DB**: ChromaDB for semantic search
- **Cache**: Redis for session management
- **Embeddings**: all-mpnet-base-v2

## 🏛️ Service Architecture

### Core Services

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **eva-backend** | 8000 | FastAPI webhook server | `/health` |
| **vllm** | 8001 | Llama-3 8B inference | `/health` |
| **chromadb** | 8002 | Vector memory storage | `/api/v1/heartbeat` |
| **redis** | 6379 | Session cache | `redis-cli ping` |
| **xtts** | 8020 | Text-to-speech | `/health` |
| **caddy** | 80/443 | Reverse proxy + TLS | Auto |

### Personality System

Eva Lite supports 3 distinct personality modes via LoRA adapters:

1. **Friendly** (`eva-friendly`)
   - Warm, conversational, empathetic
   - Temperature: 0.8, Creative responses

2. **Formal** (`eva-formal`) 
   - Professional, structured, authoritative
   - Temperature: 0.4, Consistent responses

3. **Gen-Z** (`eva-genz`)
   - Casual, trendy, internet-savvy
   - Temperature: 0.9, Expressive responses

## 🛠️ API Reference

### Main Endpoints

```bash
# Health and Status
GET  /health              # Basic health check
GET  /status              # Comprehensive system status
GET  /metrics             # Performance metrics

# Telegram Integration
POST /webhook             # Main webhook endpoint
POST /set-webhook         # Configure Telegram webhook

# LoRA Management
POST /lora/switch         # Switch personality adapter
GET  /lora/adapters       # List available adapters

# Documentation
GET  /docs               # OpenAPI documentation
GET  /redoc              # Alternative API docs
```

### Response Format

```json
{
  "success": true,
  "response": "Generated response text",
  "source": "local_gpu",
  "model": "llama-3-8b",
  "reasoning_type": "analytical",
  "personality_optimized": true,
  "lora_adapter": "eva-friendly",
  "performance": {
    "response_time": 1.8,
    "target_met": true
  }
}
```

## 📊 Monitoring & Operations

### Health Monitoring

```bash
# Check all services
curl http://localhost:8000/status

# Individual service health
docker-compose ps
docker-compose logs -f eva-backend

# Performance metrics
curl http://localhost:8000/metrics
```

### Log Management

```bash
# View logs
docker-compose logs -f [service_name]

# Log locations
./logs/eva-backend.log     # Application logs
./logs/caddy-access.log    # Access logs
./logs/performance.log     # Performance metrics
```

### Scaling Operations

```bash
# Scale backend instances
docker-compose up -d --scale eva-backend=3

# Update configuration
docker-compose restart eva-backend

# Database maintenance
docker-compose exec chromadb chroma utils reset
docker-compose exec redis redis-cli FLUSHDB
```

## 🔒 Security Features

### Network Security
- **TLS Termination**: Automatic HTTPS via Caddy
- **Rate Limiting**: Per-IP request throttling
- **IP Whitelisting**: Admin endpoint protection
- **CORS**: Configured for webhook origins only

### Application Security
- **Non-root Containers**: All services run as non-root
- **Secret Management**: Environment-based configuration
- **Input Validation**: Comprehensive request validation
- **Error Handling**: No sensitive data in error responses

### Data Protection
- **User ID Hashing**: Privacy-preserving user identification
- **Memory Encryption**: Encrypted vector storage
- **Audit Logging**: Complete request/response tracking
- **GDPR Compliance**: User data deletion endpoints

## 💰 Cost Optimization

### Infrastructure Costs (Monthly)

| Component | Cost (₹) | Description |
|-----------|----------|-------------|
| **VPS (8GB RAM, 4 vCPU)** | 4,000 | Main application server |
| **GPU Server** | 12,000 | NVIDIA RTX 3060+ for vLLM |
| **Storage (500GB)** | 2,000 | NVMe SSD for models |
| **Bandwidth** | 1,500 | 1TB monthly transfer |
| **Monitoring** | 500 | Uptime monitoring service |
| **Total** | **₹20,000** | **Under budget** ✅ |

### Cost Optimization Features
- **Local GPU Inference**: No OpenAI costs for most requests
- **Efficient Caching**: Reduced computation overhead
- **Model Optimization**: LoRA adapters vs full fine-tuning
- **Resource Limits**: Prevent cost overruns

## 🚨 Troubleshooting

### Common Issues

#### vLLM Service Won't Start
```bash
# Check GPU availability
nvidia-smi

# Check memory usage
docker stats vllm

# Restart with more memory
docker-compose down vllm
docker-compose up -d vllm
```

#### Slow Response Times
```bash
# Check current performance
curl http://localhost:8000/metrics

# Monitor resource usage
docker stats

# Optimize GPU memory
# Edit docker-compose.yml: GPU_MEMORY_UTILIZATION=0.9
```

#### Webhook Not Receiving Messages
```bash
# Verify webhook URL
curl -X POST http://localhost:8000/set-webhook

# Check Caddy configuration
docker-compose logs caddy

# Test webhook endpoint
curl -X POST http://localhost:8000/webhook -d '{}'
```

### Debug Commands

```bash
# Service debugging
docker-compose exec eva-backend python eva_clean.py health
docker-compose exec vllm curl localhost:8000/health
docker-compose exec redis redis-cli info

# Performance debugging
docker-compose exec eva-backend python -m utils.performance_monitor
curl http://localhost:8000/status | jq .performance

# Network debugging
docker network ls
docker network inspect eva-network
```

## 📈 Performance Optimization

### GPU Optimization
- **Model Quantization**: 16-bit precision for speed
- **Batch Processing**: Efficient request batching
- **Memory Management**: Careful VRAM allocation
- **Model Caching**: Persistent model loading

### Response Time Optimization
- **Async Processing**: Non-blocking operations
- **Connection Pooling**: Efficient database connections
- **Edge Caching**: Redis-based response caching
- **Streaming**: Real-time audio generation

## 🔄 Updates & Maintenance

### Regular Maintenance

```bash
# Update Docker images
docker-compose pull
docker-compose up -d

# Update models
./scripts/download_models.py

# Backup data
./scripts/backup.sh

# Clean up logs
./scripts/cleanup-logs.sh
```

### Model Updates

```bash
# Update Llama model
docker-compose down vllm
# Edit docker-compose.yml with new model
docker-compose up -d vllm

# Update LoRA adapters
./scripts/train-lora.py
./scripts/deploy-adapters.sh
```

## 📚 Development

### Local Development Setup

```bash
# Development environment
./scripts/start-dev.sh start

# Run tests
cd backend
python -m pytest tests/

# Code formatting
black . && isort . && flake8 .
```

### Adding New Features

1. **Create Feature Branch**
2. **Update Service Layer**
3. **Add API Endpoints**
4. **Update Documentation**
5. **Test Performance Impact**
6. **Deploy to Production**

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Create Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: `/docs` endpoint
- **Health Check**: `/health` endpoint  
- **Metrics**: `/metrics` endpoint
- **Logs**: `docker-compose logs -f eva-backend`

---

**Eva Lite - Production Ready AI Assistant**  
*Delivering ≤2.5s text and ≤1.2s voice responses under ₹20k/month*