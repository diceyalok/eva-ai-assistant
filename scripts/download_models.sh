#!/bin/bash
# Download required AI models for Eva

set -e

echo "📦 Downloading Eva AI models..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Create models directory
mkdir -p ./data/models/embeddings
mkdir -p ./data/models/speakers

# Download Sentence Transformers model
download_embedding_model() {
    print_status "Downloading sentence-transformers model..."
    
    python3 -c "
from sentence_transformers import SentenceTransformer
import os

model_path = './data/models/embeddings'
try:
    model = SentenceTransformer('all-mpnet-base-v2')
    model.save(model_path)
    print('✅ Embedding model downloaded successfully')
except Exception as e:
    print(f'❌ Failed to download embedding model: {e}')
    exit(1)
"
}

# Download Whisper model
download_whisper_model() {
    print_status "Downloading Whisper model..."
    
    python3 -c "
import whisper
import os

try:
    model = whisper.load_model('small')
    print('✅ Whisper model downloaded successfully')
except Exception as e:
    print(f'❌ Failed to download Whisper model: {e}')
    print('Note: This is optional. STT will work with auto-download.')
"
}

# Create sample speaker files for TTS
create_speaker_samples() {
    print_status "Creating sample speaker files..."
    
    # Create placeholder speaker files (replace with actual voice samples)
    speakers=("speaker_01" "speaker_02" "speaker_03")
    
    for speaker in "${speakers[@]}"; do
        if [ ! -f "./data/models/speakers/${speaker}.wav" ]; then
            print_warning "Create voice sample: ./data/models/speakers/${speaker}.wav"
            print_warning "Use a 3-5 second voice sample for TTS cloning"
            
            # Create empty file as placeholder
            touch "./data/models/speakers/${speaker}.wav"
        fi
    done
}

# Download vLLM model (optional, will auto-download)
setup_vllm_model() {
    print_status "Setting up vLLM model configuration..."
    
    print_warning "vLLM will auto-download models on first use"
    print_warning "For production, consider pre-downloading:"
    print_warning "  huggingface-cli download microsoft/DialoGPT-medium"
    print_warning "  huggingface-cli download meta-llama/Llama-2-7b-chat-hf"
}

# Main function
main() {
    print_status "Starting model downloads..."
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required for model downloads"
        exit 1
    fi
    
    download_embedding_model
    download_whisper_model
    create_speaker_samples
    setup_vllm_model
    
    print_success "Model setup completed!"
    print_status "Next steps:"
    echo "  1. Add voice samples to ./data/models/speakers/"
    echo "  2. Configure your .env file"
    echo "  3. Run ./scripts/deploy.sh"
}

main "$@"