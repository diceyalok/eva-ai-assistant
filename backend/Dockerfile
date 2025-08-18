FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install whisper.cpp
RUN git clone https://github.com/ggerganov/whisper.cpp.git /tmp/whisper.cpp && \
    cd /tmp/whisper.cpp && \
    cmake -B build && \
    cmake --build build --config Release && \
    cp build/bin/whisper-cli /usr/local/bin/whisper && \
    cp models/download-ggml-model.sh /usr/local/bin/ && \
    rm -rf /tmp/whisper.cpp

# Download whisper model
RUN wget -P /app/models/ https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /app/audio_cache /app/logs

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]