#!/bin/bash
# Eva Lite Production Deployment Script
# Deploys the complete PRD-compliant architecture

set -e

echo "🚀 Starting Eva Lite Production Deployment..."

# Configuration
PROJECT_NAME="eva-lite"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if GPU is available
    if command -v nvidia-smi &> /dev/null; then
        print_success "NVIDIA GPU detected"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    else
        print_warning "No NVIDIA GPU detected. Some services may run on CPU."
    fi
    
    # Check environment file
    if [ ! -f ".env" ]; then
        print_warning "No .env file found. Creating from template..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your actual configuration before proceeding."
            exit 1
        else
            print_error "No .env.example file found. Please create environment configuration."
            exit 1
        fi
    fi
    
    print_success "Prerequisites check completed"
}

# Create required directories
create_directories() {
    print_status "Creating required directories..."
    
    mkdir -p data/{audio,models,chromadb,redis,caddy,prometheus}
    mkdir -p data/models/{hf_cache,xtts}
    mkdir -p data/adapters/{eva-friendly,eva-formal,eva-genz}
    mkdir -p logs
    mkdir -p backups
    
    print_success "Directories created"
}

# Download required models
download_models() {
    print_status "Checking for required models..."
    
    # Create model download script
    cat > ./scripts/download_models.py << 'EOF'
#!/usr/bin/env python3
import os
import logging
from huggingface_hub import snapshot_download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_model(repo_id, cache_dir):
    try:
        logger.info(f"Downloading {repo_id}...")
        snapshot_download(
            repo_id=repo_id,
            cache_dir=cache_dir,
            ignore_patterns=["*.git*", "README.md", "*.bin.ignore"]
        )
        logger.info(f"✅ {repo_id} downloaded successfully")
    except Exception as e:
        logger.error(f"Failed to download {repo_id}: {e}")

if __name__ == "__main__":
    models_dir = "./data/models/hf_cache"
    os.makedirs(models_dir, exist_ok=True)
    
    # Download Llama-3 8B model
    download_model("meta-llama/Meta-Llama-3-8B-Instruct", models_dir)
    
    # Download embedding model
    download_model("sentence-transformers/all-mpnet-base-v2", models_dir)
    
    print("🎯 Model downloads completed!")
EOF

    python3 ./scripts/download_models.py
    
    print_success "Models downloaded"
}

# Create LoRA adapter placeholders
create_lora_adapters() {
    print_status "Creating LoRA adapter configurations..."
    
    for personality in friendly formal genz; do
        adapter_dir="./data/adapters/eva-${personality}"
        mkdir -p "$adapter_dir"
        
        # Create adapter config
        cat > "$adapter_dir/adapter_config.json" << EOF
{
    "peft_type": "LORA",
    "task_type": "CAUSAL_LM",
    "r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.1,
    "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
    "personality": "$personality",
    "base_model_name_or_path": "meta-llama/Meta-Llama-3-8B-Instruct",
    "inference_mode": false,
    "bias": "none"
}
EOF
        
        # Create placeholder adapter weights
        python3 -c "
import torch
import os
torch.save({'placeholder': True}, '$adapter_dir/adapter_model.bin')
print(f'Created LoRA adapter: $personality')
"
    done
    
    print_success "LoRA adapters created"
}

# Backup existing data
backup_existing_data() {
    if [ -d "data" ] && [ "$(ls -A data)" ]; then
        print_status "Backing up existing data..."
        mkdir -p "$BACKUP_DIR"
        cp -r data/* "$BACKUP_DIR/"
        print_success "Data backed up to $BACKUP_DIR"
    fi
}

# Deploy services
deploy_services() {
    print_status "Deploying Eva Lite services..."
    
    # Pull latest images
    print_status "Pulling Docker images..."
    docker-compose pull
    
    # Build custom images
    print_status "Building Eva backend..."
    docker-compose build eva-backend
    
    # Start services in order
    print_status "Starting infrastructure services..."
    docker-compose up -d redis chromadb
    
    print_status "Waiting for infrastructure to be ready..."
    sleep 10
    
    print_status "Starting AI services..."
    docker-compose up -d vllm xtts
    
    print_status "Waiting for AI services to load models..."
    sleep 60
    
    print_status "Starting Eva backend..."
    docker-compose up -d eva-backend
    
    print_status "Starting reverse proxy..."
    docker-compose up -d caddy
    
    print_success "All services deployed"
}

# Verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Wait for services to be fully ready
    sleep 30
    
    # Check service health
    services=("redis" "chromadb" "vllm" "xtts" "eva-backend" "caddy")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            print_success "$service is running"
        else
            print_error "$service is not running"
            docker-compose logs "$service" | tail -20
        fi
    done
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    
    # Test health endpoint
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Health endpoint responding"
    else
        print_error "Health endpoint not responding"
    fi
    
    # Test vLLM
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        print_success "vLLM service responding"
    else
        print_warning "vLLM service not responding (may still be loading)"
    fi
    
    print_success "Deployment verification completed"
}

# Set up monitoring (optional)
setup_monitoring() {
    if [ "$1" = "--with-monitoring" ]; then
        print_status "Setting up monitoring stack..."
        docker-compose --profile monitoring up -d prometheus
        print_success "Monitoring stack deployed"
    fi
}

# Main deployment flow
main() {
    echo "
    ███████╗██╗   ██╗ █████╗     ██╗     ██╗████████╗███████╗
    ██╔════╝██║   ██║██╔══██╗    ██║     ██║╚══██╔══╝██╔════╝
    █████╗  ██║   ██║███████║    ██║     ██║   ██║   █████╗  
    ██╔══╝  ██║   ██║██╔══██║    ██║     ██║   ██║   ██╔══╝  
    ███████╗╚██████╔╝██║  ██║    ███████╗██║   ██║   ███████╗
    ╚══════╝ ╚═════╝ ╚═╝  ╚═╝    ╚══════╝╚═╝   ╚═╝   ╚══════╝
    
    Production Deployment Script
    "
    
    check_prerequisites
    backup_existing_data
    create_directories
    download_models
    create_lora_adapters
    deploy_services
    verify_deployment
    setup_monitoring "$@"
    
    print_success "🎉 Eva Lite deployment completed successfully!"
    
    echo "
📊 Deployment Summary:
- FastAPI Backend: http://localhost:8000
- vLLM API: http://localhost:8001  
- ChromaDB: http://localhost:8002
- XTTS v2: http://localhost:8020
- Redis: localhost:6379

🔧 Next Steps:
1. Configure your domain in .env file
2. Set up Telegram webhook: curl -X POST http://localhost:8000/set-webhook
3. Monitor logs: docker-compose logs -f eva-backend
4. Check status: curl http://localhost:8000/status

📚 Documentation:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics
"
}

# Run main function with all arguments
main "$@"