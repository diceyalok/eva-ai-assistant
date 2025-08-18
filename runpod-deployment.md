# Eva RunPod Deployment Guide

## 🚀 RunPod Setup for Better Performance

### **Why RunPod?**
- **GPU Access**: A100/RTX 4090 for faster local AI models
- **Better Performance**: 10x faster model loading and inference
- **Cost Effective**: Pay only for usage (~$0.50-2/hour)
- **Scalability**: Auto-scaling based on demand

### **Current Performance Issues:**
- Voice processing: 3+ seconds (target: 1.2s)
- Model loading: 400MB reloads (should be cached)
- Memory operations: 200-500ms delays

---

## 📋 Deployment Plan

### **Phase 1: Container Preparation**
1. **Optimize Docker Images**
   - Multi-stage builds to reduce size
   - Pre-download models in image
   - Optimize Python dependencies

2. **GPU-Optimized Configuration**
   - CUDA-enabled PyTorch
   - Optimized vLLM settings
   - GPU memory management

### **Phase 2: RunPod Template**
```dockerfile
# Eva RunPod Template
FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y python3.10 python3-pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
RUN python -c "import whisper; whisper.load_model('small')"

# Copy Eva code
COPY . /app
WORKDIR /app

# Configure for GPU
ENV CUDA_VISIBLE_DEVICES=0
ENV TORCH_CUDA_ARCH_LIST="7.5;8.0;8.6"

EXPOSE 8000
CMD ["python", "eva_clean.py", "webhook"]
```

### **Phase 3: Performance Optimizations**

#### **Model Optimization:**
```python
# GPU-optimized model loading
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
embedding_model = SentenceTransformer('all-mpnet-base-v2').to(device)
whisper_model = whisper.load_model("small").cuda()
```

#### **Memory Optimization:**
```python
# Batch processing for embeddings
async def batch_embeddings(texts: List[str], batch_size=32):
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = embedding_model.encode(batch)
        embeddings.extend(batch_embeddings)
    return embeddings
```

#### **Voice Pipeline Optimization:**
```python
# Streaming voice processing
async def process_voice_streaming(audio_path: str):
    # Use GPU for transcription
    result = whisper_model.transcribe(audio_path, fp16=True)
    return result["text"]
```

---

## 💰 Cost Analysis

### **Current Local Setup:**
- Electricity: ~₹5000/month
- Performance: Limited by CPU/RAM
- Availability: 95% (power outages, maintenance)

### **RunPod Setup:**
- GPU Instance: ₹50-150/hour
- Usage: ~200 hours/month = ₹10,000-30,000/month
- Performance: 10x faster
- Availability: 99.9%

### **Hybrid Approach (Recommended):**
- Development: Local
- Production: RunPod
- Estimated cost: ₹15,000/month for production

---

## 🛠 Implementation Steps

### **Step 1: Prepare RunPod Template**
1. Create optimized Dockerfile
2. Test locally with GPU
3. Upload to RunPod

### **Step 2: Environment Configuration**
```bash
# Environment variables for RunPod
TELEGRAM_BOT_TOKEN=your_token
OPENAI_API_KEY=your_key
REDIS_URL=redis://redis:6379
CHROMA_HOST=localhost
CHROMA_PORT=8000
WEBHOOK_URL=https://your-runpod-url.com/webhook
```

### **Step 3: Webhook Mode Setup**
```python
# Switch from polling to webhook for production
app.run_webhook(
    listen="0.0.0.0",
    port=8000,
    url_path="webhook",
    webhook_url=f"{WEBHOOK_URL}/webhook"
)
```

### **Step 4: Monitoring & Scaling**
- CloudWatch/Grafana monitoring
- Auto-scaling based on load
- Health checks and alerting

---

## 🎯 Expected Performance Gains

| Metric | Current | RunPod Target | Improvement |
|--------|---------|---------------|-------------|
| Voice Processing | 3.0s | 0.8s | 3.75x faster |
| Model Loading | 6.0s | 0.5s | 12x faster |
| Memory Search | 0.5s | 0.1s | 5x faster |
| Concurrent Users | 2-3 | 50+ | 20x scale |

---

## 🚀 Next Steps

1. **Fix current web search issues**
2. **Create RunPod-optimized Docker image**
3. **Test performance on RunPod**
4. **Gradual migration plan**
5. **Production deployment**

Ready to proceed? 🎯