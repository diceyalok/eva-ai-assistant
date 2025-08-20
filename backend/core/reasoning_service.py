"""
ReasoningService - Dedicated reasoning layer for Eva Lite
Handles complex reasoning tasks, context analysis, and decision making per PRD
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from .model_manager import model_manager
from .config_manager import config
from .memory_service import memory_service

logger = logging.getLogger(__name__)

class ReasoningService:
    """Dedicated reasoning layer with advanced cognitive capabilities"""
    
    def __init__(self):
        self._initialized = False
        self.reasoning_types = {
            "analytical": "Break down complex problems step by step",
            "creative": "Generate novel solutions and ideas", 
            "logical": "Apply formal logic and deduction",
            "intuitive": "Use pattern recognition and heuristics",
            "critical": "Evaluate arguments and evidence objectively"
        }
        
    async def initialize(self):
        """Initialize reasoning service"""
        if self._initialized:
            return
            
        # Ensure dependencies are initialized
        await model_manager.warm_up_models()
        await memory_service.initialize()
        
        self._initialized = True
        logger.info("🧠 ReasoningService initialized successfully")
    
    async def analyze_context(
        self, 
        message: str, 
        context: List[Dict],
        user_id: str
    ) -> Dict[str, Any]:
        """Analyze conversation context for reasoning insights"""
        
        if not self._initialized:
            await self.initialize()
            
        try:
            # Extract relevant memories
            memories = await memory_service.search_memories(
                query=message,
                user_id=user_id,
                limit=5
            )
            
            # Analyze conversation flow
            context_analysis = await self._analyze_conversation_flow(context)
            
            # Determine reasoning type needed
            reasoning_type = await self._determine_reasoning_type(message, context)
            
            # Extract key concepts and entities
            entities = await self._extract_entities(message, context)
            
            return {
                "memories": memories,
                "conversation_flow": context_analysis,
                "reasoning_type": reasoning_type,
                "entities": entities,
                "complexity_score": self._calculate_complexity(message, context),
                "confidence": self._calculate_confidence(context, memories)
            }
            
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            return {"error": str(e)}
    
    async def reason_and_respond(
        self,
        message: str,
        context_analysis: Dict[str, Any],
        personality: str = "friendly"
    ) -> Dict[str, Any]:
        """Apply reasoning to generate thoughtful response"""
        
        try:
            reasoning_type = context_analysis.get("reasoning_type", "analytical")
            complexity = context_analysis.get("complexity_score", 0.5)
            
            # Choose reasoning strategy based on complexity and type
            if complexity > 0.8:
                response = await self._apply_deep_reasoning(
                    message, context_analysis, reasoning_type, personality
                )
            elif complexity > 0.5:
                response = await self._apply_structured_reasoning(
                    message, context_analysis, reasoning_type, personality  
                )
            else:
                response = await self._apply_quick_reasoning(
                    message, context_analysis, personality
                )
                
            return {
                "response": response,
                "reasoning_type": reasoning_type,
                "complexity": complexity,
                "confidence": context_analysis.get("confidence", 0.7),
                "processing_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            return {
                "error": str(e),
                "fallback_response": "I apologize, but I'm having trouble processing that right now."
            }
    
    async def _analyze_conversation_flow(self, context: List[Dict]) -> Dict[str, Any]:
        """Analyze conversation patterns and flow"""
        
        if not context:
            return {"pattern": "new_conversation", "sentiment": "neutral"}
            
        try:
            # Analyze recent messages for patterns
            recent_messages = context[-5:] if len(context) > 5 else context
            
            # Extract sentiment progression
            sentiment_flow = []
            for msg in recent_messages:
                content = msg.get("content", "")
                sentiment = self._analyze_sentiment(content)
                sentiment_flow.append(sentiment)
            
            # Detect conversation patterns
            pattern = self._detect_pattern(recent_messages)
            
            # Calculate engagement level
            engagement = self._calculate_engagement(recent_messages)
            
            return {
                "pattern": pattern,
                "sentiment_flow": sentiment_flow,
                "current_sentiment": sentiment_flow[-1] if sentiment_flow else "neutral",
                "engagement_level": engagement,
                "message_count": len(context),
                "recent_topics": self._extract_topics(recent_messages)
            }
            
        except Exception as e:
            logger.error(f"Conversation flow analysis failed: {e}")
            return {"pattern": "unknown", "sentiment": "neutral"}
    
    async def _determine_reasoning_type(self, message: str, context: List[Dict]) -> str:
        """Determine the type of reasoning needed"""
        
        # Keywords that indicate different reasoning types
        analytical_keywords = ["analyze", "explain", "why", "how", "because", "reason"]
        creative_keywords = ["create", "imagine", "design", "brainstorm", "innovative"]
        logical_keywords = ["if", "then", "therefore", "conclude", "prove", "logic"]
        critical_keywords = ["evaluate", "judge", "critique", "assess", "compare"]
        
        message_lower = message.lower()
        
        # Count keyword matches
        scores = {
            "analytical": sum(1 for kw in analytical_keywords if kw in message_lower),
            "creative": sum(1 for kw in creative_keywords if kw in message_lower),
            "logical": sum(1 for kw in logical_keywords if kw in message_lower),
            "critical": sum(1 for kw in critical_keywords if kw in message_lower)
        }
        
        # Return type with highest score, default to analytical
        return max(scores, key=scores.get) if max(scores.values()) > 0 else "analytical"
    
    async def _extract_entities(self, message: str, context: List[Dict]) -> List[str]:
        """Extract key entities and concepts from message and context"""
        
        # Simple entity extraction (could be enhanced with NLP models)
        import re
        
        entities = []
        
        # Extract capitalized words (likely proper nouns)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', message)
        entities.extend(proper_nouns)
        
        # Extract technical terms and concepts
        technical_terms = re.findall(r'\b[a-z]+(?:[A-Z][a-z]*)+\b', message)  # camelCase
        entities.extend(technical_terms)
        
        return list(set(entities))  # Remove duplicates
    
    def _calculate_complexity(self, message: str, context: List[Dict]) -> float:
        """Calculate complexity score for the reasoning task"""
        
        complexity_score = 0.0
        
        # Length contributes to complexity
        complexity_score += min(len(message) / 500, 0.3)
        
        # Question marks indicate inquiry complexity
        complexity_score += min(message.count('?') * 0.1, 0.2)
        
        # Technical terms increase complexity
        technical_indicators = ['api', 'database', 'algorithm', 'function', 'class', 'method']
        complexity_score += min(sum(0.1 for term in technical_indicators if term in message.lower()), 0.2)
        
        # Context length affects complexity
        complexity_score += min(len(context) * 0.05, 0.3)
        
        return min(complexity_score, 1.0)
    
    def _calculate_confidence(self, context: List[Dict], memories: List[Dict]) -> float:
        """Calculate confidence score based on available information"""
        
        confidence = 0.5  # Base confidence
        
        # More context increases confidence
        confidence += min(len(context) * 0.1, 0.3)
        
        # Relevant memories increase confidence
        confidence += min(len(memories) * 0.05, 0.2)
        
        return min(confidence, 1.0)
    
    async def _apply_deep_reasoning(
        self, 
        message: str, 
        analysis: Dict[str, Any], 
        reasoning_type: str,
        personality: str
    ) -> str:
        """Apply deep reasoning for complex queries"""
        
        reasoning_prompt = f"""
{self.reasoning_types[reasoning_type]}

Context Analysis:
- Reasoning Type: {reasoning_type}
- Complexity: High
- Entities: {', '.join(analysis.get('entities', []))}
- Memories: {len(analysis.get('memories', []))} relevant memories found

User Query: {message}

Please provide a thorough, well-reasoned response using {reasoning_type} reasoning.
Consider multiple perspectives and provide step-by-step analysis where appropriate.
"""
        
        # Return the reasoning prompt directly to avoid circular dependency
        # The AI service will handle the actual generation
        return reasoning_prompt
    
    async def _apply_structured_reasoning(
        self,
        message: str,
        analysis: Dict[str, Any],
        reasoning_type: str, 
        personality: str
    ) -> str:
        """Apply structured reasoning for moderate complexity"""
        
        reasoning_prompt = f"""
Using {reasoning_type} reasoning approach:

Query: {message}
Key Entities: {', '.join(analysis.get('entities', []))}

Please provide a clear, structured response that addresses the query methodically.
"""
        
        # Return the reasoning prompt directly to avoid circular dependency
        return reasoning_prompt
    
    async def _apply_quick_reasoning(
        self,
        message: str,
        analysis: Dict[str, Any],
        personality: str
    ) -> str:
        """Apply quick reasoning for simple queries"""
        
        # For quick reasoning, just return the original message
        return message
    
    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis"""
        
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "happy", "love"]
        negative_words = ["bad", "terrible", "awful", "hate", "sad", "angry", "frustrated"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _detect_pattern(self, messages: List[Dict]) -> str:
        """Detect conversation patterns"""
        
        if len(messages) < 2:
            return "new_conversation"
            
        # Simple pattern detection based on message characteristics
        question_count = sum(1 for msg in messages if '?' in msg.get("content", ""))
        
        if question_count > len(messages) * 0.7:
            return "inquiry_heavy"
        elif len(messages) > 10:
            return "extended_conversation"
        else:
            return "normal_conversation"
    
    def _calculate_engagement(self, messages: List[Dict]) -> float:
        """Calculate user engagement level"""
        
        if not messages:
            return 0.5
            
        # Calculate based on message length and frequency
        avg_length = sum(len(msg.get("content", "")) for msg in messages) / len(messages)
        engagement = min(avg_length / 100, 1.0)  # Normalize to 0-1
        
        return engagement
    
    def _extract_topics(self, messages: List[Dict]) -> List[str]:
        """Extract main topics from recent messages"""
        
        # Simple topic extraction (could be enhanced with NLP)
        all_text = " ".join(msg.get("content", "") for msg in messages)
        
        # Common topic keywords
        topic_keywords = {
            "technology": ["ai", "computer", "software", "code", "programming"],
            "personal": ["i", "me", "my", "personal", "life"],
            "help": ["help", "how", "question", "problem", "issue"],
            "learning": ["learn", "study", "understand", "explain", "teach"]
        }
        
        topics = []
        for topic, keywords in topic_keywords.items():
            if any(keyword in all_text.lower() for keyword in keywords):
                topics.append(topic)
        
        return topics

# Global instance
reasoning_service = ReasoningService()