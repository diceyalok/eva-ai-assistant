"""
VoiceService - Clean voice processing with cached models
No more model reloading, efficient audio processing
"""
import asyncio
import os
import logging
import hashlib
import tempfile
from typing import Dict, Optional, Any, List
from datetime import datetime
import redis.asyncio as aioredis
from .model_manager import model_manager
from .config_manager import config

# Optional imports with graceful degradation
try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

logger = logging.getLogger(__name__)

class VoiceService:
    """Clean voice service with cached models and efficient processing"""
    
    def __init__(self):
        self._redis_pool = None
        self._initialized = False
        
        # Audio processing settings
        self.sample_rate = 16000
        self.supported_formats = ['.ogg', '.mp3', '.wav', '.m4a', '.mp4', '.webm']
        
        # Voice Activity Detection settings
        self.vad_threshold = 0.5
        self.min_speech_duration = 0.5  # seconds
        
        # TTS settings based on tone
        self.tts_speakers = {
            "friendly": "speaker_01",
            "formal": "speaker_02", 
            "gen-z": "speaker_03"
        }
    
    async def initialize(self):
        """Initialize voice service with cached models"""
        if self._initialized:
            return
        
        try:
            # Initialize Redis connection pool
            self._redis_pool = aioredis.ConnectionPool.from_url(
                config.database.redis_url,
                decode_responses=False,  # Keep binary for audio data
                max_connections=5,
                retry_on_timeout=True
            )
            
            # Warm up Whisper model through ModelManager (cached!)
            await model_manager.get_whisper_model(config.voice.whisper_model_size)
            
            self._initialized = True
            logger.info("🎯 VoiceService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize VoiceService: {e}")
            raise
    
    async def transcribe_audio(
        self, 
        file_path: str, 
        user_id: str,
        apply_vad: bool = True
    ) -> Dict[str, Any]:
        """Transcribe audio with cached Whisper model"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get cached Whisper model (no reload!)
            whisper_model = await model_manager.get_whisper_model(
                config.voice.whisper_model_size
            )
            
            # Process audio if needed
            processed_path = file_path
            if AUDIO_PROCESSING_AVAILABLE and apply_vad:
                # Convert and clean audio
                converted_path = await self._convert_audio(file_path)
                if converted_path:
                    # Apply Voice Activity Detection
                    vad_path = await self._apply_vad(converted_path)
                    processed_path = vad_path or converted_path
                    
                    # Cleanup temp conversion file
                    if converted_path != processed_path:
                        await self._cleanup_temp_files([converted_path])
            
            # Transcribe using cached model
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: whisper_model.transcribe(processed_path)
            )
            
            transcription = result.get("text", "").strip()
            
            # Cleanup processed file if it's different from original
            if processed_path != file_path:
                await self._cleanup_temp_files([processed_path])
            
            # Calculate audio duration
            duration = await self._get_audio_duration(file_path) if AUDIO_PROCESSING_AVAILABLE else 0.0
            
            # Store processing stats
            await self._update_voice_stats(user_id, "transcription", duration)
            
            logger.info(f"✅ Audio transcribed for user {user_id[:8]}... | {len(transcription)} chars")
            
            return {
                "success": True,
                "transcription": transcription,
                "duration": duration,
                "confidence": result.get("language_probability", 0.0),
                "detected_language": result.get("language", "en"),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    async def generate_speech(
        self,
        text: str,
        user_id: str,
        tone: str = "friendly"
    ) -> Dict[str, Any]:
        """Generate speech with caching"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Check cache first
            cache_key = self._generate_tts_cache_key(text, tone)
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            
            cached_audio = await redis.get(f"tts_cache:{cache_key}")
            if cached_audio:
                # Return cached audio
                temp_path = await self._write_cached_audio(cached_audio)
                logger.debug(f"✅ TTS cache hit for user {user_id[:8]}...")
                
                return {
                    "success": True,
                    "audio_path": temp_path,
                    "source": "cache",
                    "tone": tone,
                    "text_length": len(text),
                    "generated_at": datetime.utcnow().isoformat()
                }
            
            # Generate new speech
            audio_path = await self._generate_tts_audio(text, tone)
            if not audio_path:
                return {
                    "success": False,
                    "error": "TTS generation failed",
                    "generated_at": datetime.utcnow().isoformat()
                }
            
            # Cache the generated audio
            await self._cache_generated_audio(cache_key, audio_path)
            
            # Update stats
            await self._update_voice_stats(user_id, "generation", 0.0)
            
            logger.info(f"✅ TTS generated for user {user_id[:8]}... | {len(text)} chars")
            
            return {
                "success": True,
                "audio_path": audio_path,
                "source": "generated",
                "tone": tone,
                "text_length": len(text),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    async def _convert_audio(self, input_path: str) -> Optional[str]:
        """Convert audio to WAV format using ffmpeg"""
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="eva_audio_")
            os.close(temp_fd)
            
            # FFmpeg conversion command
            cmd = [
                "ffmpeg", "-i", input_path,
                "-ar", str(self.sample_rate),
                "-ac", "1",  # Mono
                "-f", "wav",
                "-y",  # Overwrite
                temp_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.debug(f"✅ Audio converted: {input_path} -> {temp_path}")
                return temp_path
            else:
                logger.warning(f"FFmpeg conversion failed: {stderr.decode()}")
                os.unlink(temp_path)
                return None
                
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            return None
    
    async def _apply_vad(self, audio_path: str) -> Optional[str]:
        """Apply Voice Activity Detection to remove silence"""
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Simple energy-based VAD
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = int(0.010 * sr)   # 10ms hop
            
            # Calculate frame energy
            energy = []
            for i in range(0, len(audio) - frame_length, hop_length):
                frame = audio[i:i + frame_length]
                frame_energy = sum(frame ** 2)
                energy.append(frame_energy)
            
            if not energy:
                return None
            
            # Normalize energy
            import numpy as np
            energy = np.array(energy)
            energy = (energy - np.min(energy)) / (np.max(energy) - np.min(energy) + 1e-8)
            
            # Find speech segments
            speech_frames = energy > self.vad_threshold
            min_frames = int(self.min_speech_duration * sr / hop_length)
            speech_segments = self._find_speech_segments(speech_frames, min_frames)
            
            if not speech_segments:
                logger.debug("No speech segments found in VAD")
                return None
            
            # Extract speech audio
            speech_audio = []
            for start_frame, end_frame in speech_segments:
                start_sample = start_frame * hop_length
                end_sample = min(end_frame * hop_length, len(audio))
                speech_audio.extend(audio[start_sample:end_sample])
            
            if not speech_audio:
                return None
            
            # Save cleaned audio
            temp_fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="eva_vad_")
            os.close(temp_fd)
            
            sf.write(temp_path, np.array(speech_audio), self.sample_rate)
            logger.debug(f"✅ VAD applied: {len(speech_segments)} segments found")
            
            return temp_path
            
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return None
    
    def _find_speech_segments(self, speech_frames, min_frames: int) -> List[tuple]:
        """Find continuous speech segments"""
        segments = []
        start = None
        
        for i, is_speech in enumerate(speech_frames):
            if is_speech and start is None:
                start = i
            elif not is_speech and start is not None:
                if i - start >= min_frames:
                    segments.append((start, i))
                start = None
        
        # Handle speech continuing to end
        if start is not None and len(speech_frames) - start >= min_frames:
            segments.append((start, len(speech_frames)))
        
        return segments
    
    async def _generate_tts_audio(self, text: str, tone: str) -> Optional[str]:
        """Generate TTS audio using best available method"""
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="eva_tts_")
            os.close(temp_fd)
            
            # Try different TTS methods in order of preference
            import platform
            system = platform.system().lower()
            
            # Try XTTS server first (if configured)
            xtts_server_url = os.getenv("XTTS_SERVER_URL")
            if xtts_server_url:
                audio_path = await self._generate_xtts_via_api(text, tone, temp_path, xtts_server_url)
                if audio_path:
                    return audio_path
            
            # Try Windows SAPI (fastest, zero setup)
            if system == "windows":
                audio_path = await self._generate_windows_sapi(text, temp_path)
                if audio_path:
                    return audio_path
            
            # Try espeak on Linux
            if system == "linux":
                audio_path = await self._generate_espeak(text, temp_path)
                if audio_path:
                    return audio_path
            
            # Cleanup temp file if all methods failed
            os.unlink(temp_path)
            return None
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
    
    async def _generate_xtts_via_api(self, text: str, tone: str, output_path: str, server_url: str) -> Optional[str]:
        """Generate TTS via XTTS server API"""
        try:
            import httpx
            
            speaker = self.tts_speakers.get(tone, self.tts_speakers["friendly"])
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{server_url}/tts",
                    json={
                        "text": text,
                        "speaker_wav": f"/app/models/speakers/{speaker}.wav",
                        "language": "en"
                    }
                )
                
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    logger.debug(f"✅ XTTS API generated: {text[:50]}...")
                    return output_path
                else:
                    logger.warning(f"XTTS API failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.debug(f"XTTS API error: {e}")
            return None
    
    async def _generate_windows_sapi(self, text: str, output_path: str) -> Optional[str]:
        """Generate TTS using Windows SAPI"""
        try:
            # Limit text length for TTS
            if len(text) > 500:
                text = text[:500] + "..."
            
            # Escape text for PowerShell - be more careful with special characters
            escaped_text = text.replace('"', "'").replace('`', "'").replace('$', 'S')
            escaped_path = output_path.replace("\\", "/")
            
            ps_script = f'''
Add-Type -AssemblyName System.speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = 0
$speak.Volume = 100
$speak.SetOutputToWaveFile("{escaped_path}")
$speak.Speak("{escaped_text}")
$speak.Dispose()
'''
            
            process = await asyncio.create_subprocess_exec(
                "powershell.exe", "-Command", ps_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                logger.info(f"✅ Windows SAPI TTS generated successfully")
                return output_path
            else:
                logger.error(f"Windows SAPI failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Windows SAPI error: {e}")
            return None
    
    async def _generate_espeak(self, text: str, output_path: str) -> Optional[str]:
        """Generate TTS using espeak (Linux)"""
        try:
            cmd = [
                "espeak",
                "-w", output_path,
                "-s", "150",  # Speed
                "-v", "en+f3",  # Female voice
                text
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                logger.debug(f"✅ espeak generated: {text[:50]}...")
                return output_path
            else:
                logger.debug(f"espeak failed: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.debug(f"espeak error: {e}")
            return None
    
    def _generate_tts_cache_key(self, text: str, tone: str) -> str:
        """Generate cache key for TTS"""
        content = f"{text}_{tone}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _write_cached_audio(self, audio_data: bytes) -> str:
        """Write cached audio data to temp file"""
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav", prefix="eva_cached_")
        os.close(temp_fd)
        
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(audio_data)
        else:
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
        
        return temp_path
    
    async def _cache_generated_audio(self, cache_key: str, audio_path: str):
        """Cache generated audio for future use"""
        try:
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(audio_path, 'rb') as f:
                    audio_data = await f.read()
            else:
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()
            
            # Cache with TTL
            await redis.setex(
                f"tts_cache:{cache_key}",
                config.voice.audio_cache_ttl,
                audio_data
            )
            
            logger.debug(f"✅ Audio cached: {cache_key}")
            
        except Exception as e:
            logger.debug(f"Audio caching failed: {e}")
    
    async def _get_audio_duration(self, file_path: str) -> float:
        """Get audio file duration in seconds"""
        try:
            audio, sr = librosa.load(file_path, sr=None)
            return len(audio) / sr
        except Exception:
            return 0.0
    
    async def _update_voice_stats(self, user_id: str, operation: str, duration: float):
        """Update voice processing statistics"""
        try:
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            stats_key = f"voice_stats:{user_id}"
            
            await redis.hincrby(stats_key, f"total_{operation}", 1)
            if duration > 0:
                await redis.hincrbyfloat(stats_key, "total_duration", duration)
            await redis.hset(stats_key, "last_activity", datetime.utcnow().isoformat())
            await redis.expire(stats_key, 86400 * 30)  # 30 days
            
        except Exception as e:
            logger.debug(f"Stats update failed: {e}")
    
    async def _cleanup_temp_files(self, file_paths: List[str]):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.debug(f"Temp file cleanup failed {file_path}: {e}")
    
    async def get_voice_stats(self, user_id: str) -> Dict[str, Any]:
        """Get voice processing statistics"""
        try:
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            
            # Get user stats
            stats_key = f"voice_stats:{user_id}"
            user_stats = await redis.hgetall(stats_key)
            
            # Get cache stats
            cache_keys = await redis.keys("tts_cache:*")
            
            return {
                "initialized": self._initialized,
                "whisper_model": config.voice.whisper_model_size,
                "tts_enabled": config.voice.tts_enabled,
                "user_stats": {
                    "total_transcription": int(user_stats.get(b"total_transcription", 0)),
                    "total_generation": int(user_stats.get(b"total_generation", 0)),
                    "total_duration": float(user_stats.get(b"total_duration", 0)),
                    "last_activity": user_stats.get(b"last_activity", b"Never").decode()
                },
                "cache_entries": len(cache_keys),
                "audio_processing": AUDIO_PROCESSING_AVAILABLE,
                "aiofiles_available": AIOFILES_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Failed to get voice stats: {e}")
            return {"error": str(e)}
    
    async def clear_voice_cache(self, pattern: str = "*") -> int:
        """Clear voice cache entries"""
        try:
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            cache_keys = await redis.keys(f"tts_cache:{pattern}")
            
            if cache_keys:
                await redis.delete(*cache_keys)
                logger.info(f"✅ Cleared {len(cache_keys)} voice cache entries")
                return len(cache_keys)
            
            return 0
            
        except Exception as e:
            logger.error(f"Voice cache clear failed: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, str]:
        """Check health of voice service components"""
        health = {
            "service": "unknown",
            "whisper": "unknown",
            "redis": "unknown",
            "ffmpeg": "unknown",
            "audio_libs": "unknown"
        }
        
        try:
            # Service status
            health["service"] = "healthy" if self._initialized else "not_initialized"
            
            # Whisper model status
            try:
                await model_manager.get_whisper_model(config.voice.whisper_model_size)
                health["whisper"] = "healthy"
            except Exception:
                health["whisper"] = "unhealthy"
            
            # Redis status
            if self._redis_pool:
                try:
                    redis = aioredis.Redis(connection_pool=self._redis_pool)
                    await redis.ping()
                    health["redis"] = "healthy"
                except Exception:
                    health["redis"] = "unhealthy"
            else:
                health["redis"] = "not_initialized"
            
            # FFmpeg status
            try:
                process = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                health["ffmpeg"] = "healthy" if process.returncode == 0 else "unhealthy"
            except Exception:
                health["ffmpeg"] = "unavailable"
            
            # Audio libraries status
            health["audio_libs"] = "available" if AUDIO_PROCESSING_AVAILABLE else "limited"
            
        except Exception as e:
            logger.error(f"Voice health check failed: {e}")
            health["service"] = "error"
        
        return health
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._redis_pool:
            await self._redis_pool.disconnect()
        logger.info("VoiceService cleaned up")

# Singleton instance
voice_service = VoiceService()