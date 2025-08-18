@echo off
REM Eva RunPod Deployment Script - Windows Version

echo 🚀 Starting Eva RunPod Deployment...

REM Configuration
set DOCKER_IMAGE=eva-ai-runpod
set DOCKER_TAG=latest

echo [INFO] Building Docker image for RunPod...

REM Step 1: Build Docker image
docker build -f Dockerfile.runpod -t %DOCKER_IMAGE%:%DOCKER_TAG% .

if %ERRORLEVEL% neq 0 (
    echo [ERROR] ❌ Docker build failed
    pause
    exit /b 1
)

echo [INFO] ✅ Docker image built successfully

REM Step 2: Test image locally
echo [INFO] Testing Docker image locally...
docker run --rm -d --name eva-test -p 8000:8000 -e TELEGRAM_BOT_TOKEN=test -e OPENAI_API_KEY=test %DOCKER_IMAGE%:%DOCKER_TAG%

timeout /t 10 >nul

REM Check if container is running
docker ps | findstr eva-test >nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] ✅ Container test successful
    docker stop eva-test >nul
) else (
    echo [WARNING] ⚠️ Container test failed, but continuing...
)

REM Step 3: Generate deployment guide
echo [INFO] Generating deployment instructions...

echo # 🚀 Eva RunPod Deployment Guide > runpod-instructions.txt
echo. >> runpod-instructions.txt
echo ## Next Steps: >> runpod-instructions.txt
echo 1. Go to RunPod.io and create account >> runpod-instructions.txt
echo 2. Create new template with these settings: >> runpod-instructions.txt
echo    - Image: %DOCKER_IMAGE%:%DOCKER_TAG% >> runpod-instructions.txt
echo    - Container Disk: 20GB >> runpod-instructions.txt
echo    - Expose HTTP Port: 8000 >> runpod-instructions.txt
echo    - Command: python eva_webhook.py >> runpod-instructions.txt
echo. >> runpod-instructions.txt
echo ## Environment Variables: >> runpod-instructions.txt
echo TELEGRAM_BOT_TOKEN=your_bot_token >> runpod-instructions.txt
echo OPENAI_API_KEY=your_openai_key >> runpod-instructions.txt
echo WEBHOOK_URL=https://your-runpod-url.com >> runpod-instructions.txt
echo CUDA_VISIBLE_DEVICES=0 >> runpod-instructions.txt
echo. >> runpod-instructions.txt
echo ## After Deployment: >> runpod-instructions.txt
echo 1. Get your RunPod endpoint URL >> runpod-instructions.txt
echo 2. Update WEBHOOK_URL environment variable >> runpod-instructions.txt
echo 3. Call POST /set-webhook to configure Telegram >> runpod-instructions.txt
echo 4. Test with GET /health endpoint >> runpod-instructions.txt

echo.
echo ✅ Deployment preparation complete!
echo 📖 Check runpod-instructions.txt for next steps
echo.
echo 🎯 Quick Summary:
echo 1. ✅ Docker image built: %DOCKER_IMAGE%:%DOCKER_TAG%
echo 2. 📋 Instructions generated
echo 3. 🚀 Ready for RunPod deployment
echo.
echo Next: Upload to RunPod and configure environment variables
pause