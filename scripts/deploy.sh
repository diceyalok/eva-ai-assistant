#!/bin/bash
# Eva Production Deployment Script

set -e  # Exit on any error

echo "🚀 Starting Eva deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if running as root (needed for some operations)
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Consider using a non-root user for security."
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please copy .env.example to .env and configure it."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Create required directories
create_directories() {
    print_status "Creating required directories..."
    
    directories=(
        "./data/models"
        "./data/audio_cache"
        "./data/chroma"
        "./data/redis"
        "./logs"
        "./configs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
    
    print_success "Directories created"
}

# Set permissions
set_permissions() {
    print_status "Setting proper permissions..."
    
    # Make sure the application can write to data directories
    chmod -R 755 ./data
    chmod -R 755 ./logs
    
    # Make scripts executable
    find ./scripts -name "*.sh" -exec chmod +x {} \;
    
    print_success "Permissions set"
}

# Pull latest images
pull_images() {
    print_status "Pulling latest Docker images..."
    
    docker-compose pull
    
    print_success "Images pulled"
}

# Build custom images
build_images() {
    print_status "Building custom images..."
    
    docker-compose build --no-cache eva-api
    
    print_success "Images built"
}

# Start services
start_services() {
    print_status "Starting Eva services..."
    
    # Start in detached mode
    docker-compose up -d
    
    print_success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for API to be healthy
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Eva API is ready"
            break
        fi
        
        attempt=$((attempt + 1))
        print_status "Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 5
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Eva API failed to start within expected time"
        exit 1
    fi
    
    # Check other services
    services=("redis" "chromadb" "postgres")
    for service in "${services[@]}"; do
        if docker-compose ps $service | grep -q "Up"; then
            print_success "$service is running"
        else
            print_warning "$service may not be running properly"
        fi
    done
}

# Set up Telegram webhook
setup_webhook() {
    print_status "Setting up Telegram webhook..."
    
    # Source environment variables
    source .env
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_WEBHOOK_URL" ]; then
        print_warning "Telegram bot token or webhook URL not configured. Skipping webhook setup."
        return
    fi
    
    # Set webhook
    webhook_response=$(curl -s -X POST \
        "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
        -d "url=$TELEGRAM_WEBHOOK_URL/webhook" \
        -d "secret_token=${TELEGRAM_WEBHOOK_SECRET:-}" \
        -d "allowed_updates=[\"message\",\"callback_query\",\"inline_query\"]")
    
    if echo "$webhook_response" | grep -q '"ok":true'; then
        print_success "Telegram webhook configured successfully"
    else
        print_error "Failed to configure Telegram webhook: $webhook_response"
    fi
}

# Show status
show_status() {
    print_status "Deployment status:"
    echo
    
    docker-compose ps
    echo
    
    print_status "Service URLs:"
    echo "🔗 Eva API: http://localhost:8000"
    echo "🔗 Redis: localhost:6379"
    echo "🔗 ChromaDB: http://localhost:8001"
    echo "🔗 PostgreSQL: localhost:5432"
    echo "🔗 vLLM: http://localhost:8002"
    echo
    
    print_status "Logs:"
    echo "📋 API logs: docker-compose logs -f eva-api"
    echo "📋 All logs: docker-compose logs -f"
    echo
    
    print_success "Eva deployment completed successfully! 🎉"
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Deployment failed. Cleaning up..."
        docker-compose down
    fi
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Main deployment process
main() {
    print_status "Eva Production Deployment"
    print_status "=========================="
    
    check_privileges
    check_prerequisites
    create_directories
    set_permissions
    pull_images
    build_images
    start_services
    wait_for_services
    setup_webhook
    show_status
}

# Run main function
main "$@"