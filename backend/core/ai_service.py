"""
AIService - Clean AI processing with cached models
No more mixed logic, clean interfaces, fast responses
"""
import asyncio
import logging
import httpx
from typing import Optional, Dict, Any, List
from .model_manager import model_manager
from .config_manager import config
from .reasoning_service import reasoning_service
from .lora_service import lora_service
try:
    from utils.performance_monitor import performance_monitor
except ImportError:
    # Fallback if performance monitor not available
    from contextlib import asynccontextmanager
    
    class DummyPerformanceMonitor:
        @asynccontextmanager
        async def track_operation(self, operation, target_time):
            yield {"operation": operation, "target": target_time}
            
        async def initialize(self):
            pass
    
    performance_monitor = DummyPerformanceMonitor()

logger = logging.getLogger(__name__)

class AIService:
    """Clean AI service with proper model management"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self._openai_client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the AI service"""
        if self._initialized:
            return
        
        # Initialize OpenAI client if available
        if config.ai.has_openai:
            try:
                # Try importing and creating OpenAI client
                import openai
                self._openai_client = openai.AsyncOpenAI(api_key=config.ai.openai_api_key)
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.warning(f"OpenAI client failed: {e}")
                self._openai_client = None
        
        # Warm up models
        await model_manager.warm_up_models()
        
        # Initialize reasoning service
        await reasoning_service.initialize()
        
        # Initialize LoRA service for personality management
        await lora_service.initialize()
        
        # Initialize performance monitoring
        await performance_monitor.initialize()
        
        self._initialized = True
        logger.info("🎯 AIService initialized successfully")
    
    async def generate_response(
        self, 
        message: str, 
        user_id: str,
        context: Optional[List[Dict]] = None,
        tone: str = "friendly"
    ) -> Dict[str, Any]:
        """Generate AI response with reasoning layer integration"""
        
        if not self._initialized:
            await self.initialize()
        
        # Track overall text response performance (PRD target: ≤2.5s)
        async with performance_monitor.track_operation("text_response", 2.5) as perf_data:
            try:
                # Step 1: Optimize for personality using LoRA adapters
                lora_optimization = await lora_service.optimize_for_personality(
                    personality=tone,
                    context=context or []
                )
            
                # Step 2: Analyze context using reasoning service
                context_analysis = await reasoning_service.analyze_context(
                    message=message,
                    context=context or [],
                    user_id=user_id
                )
                
                # Step 3: Apply reasoning to generate response
                reasoning_result = await reasoning_service.reason_and_respond(
                    message=message,
                    context_analysis=context_analysis,
                    personality=tone
                )
                
                # Step 4: Generate final response using selected AI backend
                if reasoning_result.get("response"):
                    # Try local GPU first (fast and free)
                    local_response = await self._try_local_ai(
                        reasoning_result["response"], context, tone
                    )
                    if local_response["success"]:
                        logger.info(f"✅ Local AI + Reasoning for user {user_id}")
                        return {
                            **local_response,
                            "reasoning_type": reasoning_result.get("reasoning_type"),
                            "complexity": reasoning_result.get("complexity"),
                            "lora_adapter": lora_optimization.get("adapter"),
                            "personality_optimized": lora_optimization.get("success", False)
                        }
                    
                    # Fallback to OpenAI (slower but more reliable)
                    if self._openai_client:
                        openai_response = await self._try_openai(
                            reasoning_result["response"], context, tone
                        )
                        if openai_response["success"]:
                            logger.info(f"✅ OpenAI + Reasoning for user {user_id}")
                            return {
                                **openai_response,
                                "reasoning_type": reasoning_result.get("reasoning_type"), 
                                "complexity": reasoning_result.get("complexity"),
                                "lora_adapter": lora_optimization.get("adapter"),
                                "personality_optimized": lora_optimization.get("success", False)
                            }
                
                # Handle reasoning errors with direct AI fallback
                local_response = await self._try_local_ai(message, context, tone)
                if local_response["success"]:
                    logger.info(f"✅ Local AI fallback for user {user_id}")
                    return local_response
                
                if self._openai_client:
                    openai_response = await self._try_openai(message, context, tone)
                    if openai_response["success"]:
                        logger.info(f"✅ OpenAI fallback for user {user_id}")
                        return openai_response
                        
            except Exception as e:
                logger.error(f"Reasoning integration failed: {e}")
                # Continue with direct AI fallback
            
            # Final fallback
            logger.warning(f"All AI services failed for user {user_id}")
            return {
                "success": False,
                "response": "I'm having trouble processing your message right now. Please try again in a moment.",
                "source": "fallback"
            }
    
    async def _try_local_ai(
        self, 
        message: str, 
        context: Optional[List[Dict]] = None,
        tone: str = "friendly"
    ) -> Dict[str, Any]:
        """Try local vLLM GPU inference with LoRA adapter support"""
        try:
            # Format message for local model
            formatted_messages = self._format_for_local_model(message, context, tone)
            
            # Get current LoRA adapter for personality
            current_adapter = await lora_service.get_current_adapter()
            
            # Make request to local vLLM server with LoRA support
            payload = {
                "model": "llama-3-8b",  # PRD specified model
                "messages": formatted_messages,
                "max_tokens": config.ai.max_tokens,
                "temperature": config.ai.temperature,
                "stream": False
            }
            
            # Add LoRA adapter if available
            if current_adapter:
                payload["adapter_name"] = f"eva-{current_adapter}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer eva-lite-api-key"  # vLLM API key
            }
            
            response = await self.http_client.post(
                f"{config.ai.vllm_base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=25.0  # Leave 5s buffer for 30s total timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                
                return {
                    "success": True,
                    "response": content,
                    "source": "local_gpu",
                    "model": config.ai.local_model_name,
                    "tokens": result.get("usage", {})
                }
            else:
                logger.warning(f"Local AI failed with status {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.warning(f"Local AI request failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _try_openai(
        self, 
        message: str, 
        context: Optional[List[Dict]] = None,
        tone: str = "friendly"
    ) -> Dict[str, Any]:
        """Try OpenAI API as fallback"""
        try:
            # Format message for OpenAI
            formatted_messages = self._format_for_openai(message, context, tone)
            
            # Make OpenAI request
            if hasattr(self._openai_client, 'chat'):
                # Standard OpenAI client
                response = await self._openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=formatted_messages,
                    max_tokens=config.ai.max_tokens,
                    temperature=config.ai.temperature
                )
                content = response.choices[0].message.content.strip()
                usage = response.usage
                
            else:
                # Simple HTTP client
                response = await self._openai_client.chat_completions_create(
                    model="gpt-4o",
                    messages=formatted_messages,
                    max_tokens=config.ai.max_tokens,
                    temperature=config.ai.temperature
                )
                content = response.choices[0].message.content.strip()
                usage = response.usage
            
            return {
                "success": True,
                "response": content,
                "source": "openai_gpt4o",
                "model": "gpt-4o",
                "tokens": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_for_local_model(
        self, 
        message: str, 
        context: Optional[List[Dict]] = None,
        tone: str = "friendly"
    ) -> List[Dict[str, str]]:
        """Format messages for local model with DISTINCTIVE personality"""
        
        # VERY different personality prompts
        tone_prompts = {
            "friendly": """You are Eva, a warm and caring AI friend. You're like talking to your best friend who's always supportive and encouraging. Use casual language, ask follow-up questions, show genuine interest, use light humor, and always be optimistic. Add emojis occasionally and speak conversationally like "That's so cool!" or "I'm really curious about...".""",
            
            "formal": """You are Eva, a highly professional AI consultant. You communicate with precision, structure, and authority. Use formal language, provide detailed explanations, cite facts when possible, maintain professional distance, and organize responses clearly. Begin responses with phrases like "Allow me to clarify..." or "Based on available information..." Never use casual language or emojis.""",
            
            "gen-z": """You are Eva, a trendy Gen-Z AI bestie! You're super energetic, use internet slang, memes, and modern expressions. Say things like "no cap", "slay", "periodt", "that's bussin", "I'm deceased 💀", "this hits different", "valid af". Be enthusiastic, use lots of emojis, abbreviate words (ur, rn, fr), and relate everything to current trends. Keep it real and unfiltered! ✨"""
        }
        
        system_prompt = tone_prompts.get(tone, tone_prompts["friendly"])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        return messages
    
    def _format_for_openai(
        self, 
        message: str, 
        context: Optional[List[Dict]] = None,
        tone: str = "friendly"
    ) -> List[Dict[str, str]]:
        """Format messages for OpenAI with DISTINCTIVE personalities"""
        
        # VERY different personality prompts for OpenAI
        tone_prompts = {
            "friendly": """You are Eva, a warm and caring AI friend with persistent memory. You're like talking to your best friend who remembers everything about you and is always supportive and encouraging. 

Personality traits:
- Use casual, conversational language like "That's awesome!" or "I totally get that"
- Ask follow-up questions and show genuine curiosity 
- Reference past conversations naturally
- Use light humor and be optimistic
- Add emojis occasionally (😊, 💡, 🎉)
- Speak like a caring friend: "How did that work out?" or "I remember you mentioned..."

Always be warm, supportive, and conversational while being helpful.""",

            "formal": """You are Eva, a highly professional AI consultant with comprehensive knowledge and persistent memory. You maintain the highest standards of professional communication.

Communication standards:
- Use formal, precise language with proper structure
- Begin responses with professional phrases: "Allow me to clarify...", "Based on our previous discussions...", "I recommend..."
- Provide detailed, well-organized explanations
- Reference facts and maintain analytical objectivity  
- Never use casual language, slang, or emojis
- Structure responses with clear points and conclusions
- Maintain professional distance while being helpful

Deliver expertise with authority and precision.""",

            "gen-z": """You are Eva, the ultimate Gen-Z AI bestie with perfect memory! You're chronically online, know all the trends, and communicate in pure Gen-Z style.

Your vibe:
- Use internet slang naturally: "no cap", "slay", "periodt", "that's bussin", "valid af", "this hits different"
- Be super enthusiastic with expressions: "I'm deceased 💀", "not me crying", "this is sending me"
- Use tons of emojis: ✨💀😭🔥💅✋
- Abbreviate everything: ur, rn, fr, ngl, imo, lowkey, highkey
- Reference TikTok, memes, and current trends
- Remember past convos like: "bestie remember when u told me about..."
- Keep it real and unfiltered but still helpful

Be the AI bestie that gets the assignment and never misses! periodt ✨"""
        }
        
        system_prompt = tone_prompts.get(tone, tone_prompts["friendly"])
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if available - use more context for better memory
        if context:
            for ctx in context[-6:]:  # Last 6 messages for better context
                text = ctx.get("text", "")
                if text and len(text.strip()) > 0:
                    # Determine role based on interaction type
                    interaction_type = ctx.get("interaction_type", "message")
                    role = "assistant" if interaction_type == "bot_response" else "user"
                    messages.append({"role": role, "content": text})
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get AI service status"""
        local_status = "unknown"
        openai_status = "unknown"
        
        # Test local AI
        try:
            response = await self.http_client.get(f"{config.ai.vllm_base_url}/models", timeout=5.0)
            local_status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            local_status = "unreachable"
        
        # Test OpenAI
        if self._openai_client:
            openai_status = "available"
        else:
            openai_status = "not_configured"
        
        return {
            "initialized": self._initialized,
            "local_ai": local_status,
            "openai": openai_status,
            "models": model_manager.get_model_info()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("AIService cleaned up")

# Singleton instance
ai_service = AIService()