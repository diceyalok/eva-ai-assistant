#!/usr/bin/env python3
"""
Voice Debug Test - Test voice transcription and TTS separately
"""
import asyncio
import logging
import tempfile
import os
from core import voice_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_tts_only():
    """Test just TTS generation"""
    print("🎤 Testing TTS generation...")
    
    try:
        await voice_service.initialize()
        print("✅ Voice service initialized")
        
        # Test simple TTS
        result = await voice_service.generate_speech(
            text="Hello, this is a test of Eva's voice generation system.",
            user_id="test_user",
            tone="friendly"
        )
        
        if result["success"]:
            print(f"✅ TTS Success: {result['audio_path']}")
            print(f"   Source: {result['source']}")
            print(f"   Tone: {result['tone']}")
            
            # Check if file exists and has content
            if os.path.exists(result["audio_path"]):
                file_size = os.path.getsize(result["audio_path"])
                print(f"   File size: {file_size} bytes")
                
                if file_size > 1000:
                    print("✅ Audio file looks good!")
                else:
                    print("❌ Audio file too small")
            else:
                print("❌ Audio file doesn't exist")
                
        else:
            print(f"❌ TTS Failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_whisper_simple():
    """Test Whisper model loading"""
    print("\n🎧 Testing Whisper model...")
    
    try:
        from core import model_manager
        
        # Test Whisper model loading
        whisper_model = await model_manager.get_whisper_model("small")
        print("✅ Whisper model loaded successfully")
        print(f"   Model type: {type(whisper_model)}")
        
        # Test if we can call transcribe (without actual audio)
        print("✅ Whisper model ready for transcription")
        
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_voice_health():
    """Test voice service health"""
    print("\n🏥 Testing voice service health...")
    
    try:
        await voice_service.initialize()
        health = await voice_service.health_check()
        
        print("Health check results:")
        for key, value in health.items():
            status = "✅" if value in ["healthy", "available"] else "❌"
            print(f"   {status} {key}: {value}")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")

async def main():
    """Run all voice tests"""
    print("🎯 EVA VOICE DEBUG TESTS")
    print("=" * 50)
    
    await test_whisper_simple()
    await test_voice_health()  
    await test_tts_only()
    
    print("\n" + "=" * 50)
    print("🎯 Voice tests completed!")

if __name__ == "__main__":
    asyncio.run(main())