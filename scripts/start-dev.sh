#!/bin/bash
# Eva Lite Development Quick Start
# Minimal setup for development and testing

set -e

echo "🚀 Starting Eva Lite Development Environment..."

# Colors for output
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

# Quick environment setup
setup_dev_env() {
    print_status "Setting up development environment..."
    
    # Create minimal directories
    mkdir -p data/{audio,models,chromadb,redis}
    mkdir -p logs
    
    # Check for .env file
    if [ ! -f ".env" ]; then
        print_warning "Creating development .env file..."
        cat > .env << 'EOF'
# Eva Lite Development Configuration
ENVIRONMENT=development
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEBHOOK_URL=http://localhost:8000
OPENAI_API_KEY=your_openai_key_here
VLLM_URL=http://localhost:8001
REDIS_URL=redis://localhost:6379/0
CHROMA_HOST=localhost
CHROMA_PORT=8002
DEBUG=true
EOF
        print_warning "Please edit .env file with your bot token and API keys"
    fi
    
    print_success "Development environment ready"
}

# Start minimal services for development
start_dev_services() {
    print_status "Starting development services..."
    
    # Start only essential services
    docker-compose up -d redis chromadb
    
    print_status "Waiting for services to be ready..."
    sleep 5
    
    # Optional: Start vLLM if GPU available
    if command -v nvidia-smi &> /dev/null; then
        print_status "GPU detected. Starting vLLM service..."
        docker-compose up -d vllm
        print_warning "vLLM is starting. This may take 2-3 minutes to load the model."
    else
        print_warning "No GPU detected. Using OpenAI API fallback only."
    fi
    
    print_success "Development services started"
}

# Run Eva in development mode
run_eva_dev() {
    print_status "Starting Eva in development mode..."
    
    cd backend
    
    # Install dependencies if needed
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Run in polling mode for development
    print_status "Starting Eva backend in polling mode..."
    python eva_clean.py polling
}

# Health check
check_health() {
    print_status "Checking service health..."
    
    # Check Redis
    if docker-compose ps redis | grep -q "Up"; then
        print_success "Redis is running"
    else
        print_warning "Redis is not running"
    fi
    
    # Check ChromaDB
    if docker-compose ps chromadb | grep -q "Up"; then
        print_success "ChromaDB is running"
    else
        print_warning "ChromaDB is not running"
    fi
    
    # Check vLLM (optional)
    if docker-compose ps vllm | grep -q "Up"; then
        print_success "vLLM is running"
    else
        print_warning "vLLM is not running (using OpenAI fallback)"
    fi
}

# Show development info
show_dev_info() {
    echo "
📊 Development Environment:
- Redis: localhost:6379
- ChromaDB: http://localhost:8002
- vLLM (if GPU): http://localhost:8001

🔧 Development Commands:
- Check services: docker-compose ps
- View logs: docker-compose logs redis chromadb vllm
- Stop services: docker-compose down
- Restart service: docker-compose restart <service>

🛠️ Eva Commands:
- Health check: python eva_clean.py health
- Polling mode: python eva_clean.py polling
- Webhook mode: python eva_clean.py webhook

📝 Configuration:
- Bot config: .env file
- Service config: docker-compose.yml
- Eva config: backend/core/config_manager.py
"
}

# Main function
main() {
    case "${1:-start}" in
        "start")
            setup_dev_env
            start_dev_services
            check_health
            show_dev_info
            ;;
        "run")
            run_eva_dev
            ;;
        "health")
            check_health
            ;;
        "stop")
            print_status "Stopping development services..."
            docker-compose down
            print_success "Services stopped"
            ;;
        "clean")
            print_status "Cleaning up development environment..."
            docker-compose down -v
            docker system prune -f
            print_success "Environment cleaned"
            ;;
        *)
            echo "Usage: $0 [start|run|health|stop|clean]"
            echo "  start  - Set up and start development services"
            echo "  run    - Run Eva backend in development mode"
            echo "  health - Check service health"
            echo "  stop   - Stop all services"
            echo "  clean  - Clean up everything"
            ;;
    esac
}

main "$@"