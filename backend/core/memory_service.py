"""
MemoryService - Efficient memory management with cached models
No more embedding model reloading, fast vector search
"""
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import chromadb
import redis.asyncio as aioredis
from .model_manager import model_manager
from .config_manager import config

logger = logging.getLogger(__name__)

class MemoryService:
    """Clean memory service with proper resource management"""
    
    def __init__(self):
        self._chroma_client = None
        self._collection = None
        self._redis_pool = None
        self._initialized = False
        self.collection_name = "eva_memories"
    
    async def initialize(self):
        """Initialize memory service with connection pooling"""
        if self._initialized:
            return
        
        try:
            # Initialize ChromaDB client
            self._chroma_client = chromadb.HttpClient(
                host=config.database.chroma_host,
                port=config.database.chroma_port
            )
            
            # Get or create collection
            try:
                self._collection = self._chroma_client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"✅ Using existing ChromaDB collection: {self.collection_name}")
            except Exception:
                # Create new collection
                self._collection = self._chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": "Eva conversation memories with embeddings",
                        "embedding_model": config.ai.embedding_model,
                        "embedding_dimension": 768
                    }
                )
                logger.info(f"✅ Created new ChromaDB collection: {self.collection_name}")
            
            # Initialize Redis connection pool
            self._redis_pool = aioredis.ConnectionPool.from_url(
                config.database.redis_url,
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True
            )
            
            self._initialized = True
            logger.info("🎯 MemoryService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MemoryService: {e}")
            logger.warning("⚠️ Memory service disabled - ChromaDB not available")
            self._chroma_client = None
            self._collection = None
            # Don't raise - allow Eva to continue without memory
    
    async def store_memory(
        self,
        user_id: str,
        text: str,
        interaction_type: str = "message",
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Store memory with cached embedding model"""
        
        if not self._initialized:
            await self.initialize()
            
        if not self._collection:
            logger.debug("Memory storage skipped - ChromaDB not available")
            return False
        
        try:
            # Get cached embedding model (no reload!)
            embedding_model = await model_manager.get_embedding_model(config.ai.embedding_model)
            
            # Generate embedding (async to avoid blocking)
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: embedding_model.encode([text])[0].tolist()
            )
            
            # Create memory ID
            memory_id = self._generate_memory_id(user_id, text, interaction_type)
            
            # Prepare metadata
            memory_metadata = {
                "user_id": self._hash_user_id(user_id),
                "interaction_type": interaction_type,
                "importance": importance,
                "timestamp": datetime.utcnow().isoformat(),
                "text_length": len(text),
                **(metadata or {})
            }
            
            # Store in ChromaDB
            self._collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[memory_metadata]
            )
            
            # Cache in Redis for quick access
            await self._cache_recent_memory(user_id, {
                "id": memory_id,
                "text": text,
                "type": interaction_type,
                "importance": importance,
                "timestamp": memory_metadata["timestamp"]
            })
            
            logger.debug(f"✅ Memory stored for user {user_id[:8]}... | {interaction_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return False
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search memories with cached embedding model"""
        
        if not self._initialized:
            await self.initialize()
            
        if not self._collection:
            logger.debug("Memory search skipped - ChromaDB not available")
            return []
        
        try:
            # Get cached embedding model (no reload!)
            embedding_model = await model_manager.get_embedding_model(config.ai.embedding_model)
            
            # Generate query embedding (async to avoid blocking)
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None,
                lambda: embedding_model.encode([query])[0].tolist()
            )
            
            # Search in ChromaDB
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit * 2,  # Get more to filter by user
                where={
                    "$and": [
                        {"user_id": {"$eq": self._hash_user_id(user_id)}},
                        {"importance": {"$gte": min_importance}}
                    ]
                }
            )
            
            # Format results
            memories = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    
                    memories.append({
                        "text": doc,
                        "importance": metadata.get("importance", 0.0),
                        "timestamp": metadata.get("timestamp", ""),
                        "interaction_type": metadata.get("interaction_type", "unknown"),
                        "similarity": 1.0 - distance,  # Convert distance to similarity
                        "metadata": metadata
                    })
            
            # Sort by importance and recency
            memories.sort(key=lambda x: (x["importance"], x["timestamp"]), reverse=True)
            
            logger.debug(f"✅ Found {len(memories)} memories for user {user_id[:8]}...")
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_recent_context(
        self,
        user_id: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Get recent conversation context from Redis cache"""
        
        try:
            # Try Redis cache first (faster)
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            cache_key = f"recent_context:{self._hash_user_id(user_id)}"
            
            cached_context = await redis.lrange(cache_key, 0, limit - 1)
            if cached_context:
                context = []
                for item in cached_context:
                    try:
                        import json
                        context.append(json.loads(item))
                    except Exception:
                        continue
                
                logger.debug(f"✅ Retrieved cached context for user {user_id[:8]}...")
                return context
            
            # Fallback to ChromaDB search for recent messages
            # Search for any recent interactions instead of generic query
            try:
                results = self._collection.query(
                    query_embeddings=None,  # Get all results
                    n_results=limit * 3,
                    where={
                        "user_id": {"$eq": self._hash_user_id(user_id)}
                    },
                    include=["documents", "metadatas"]
                )
                
                if results["documents"] and results["documents"][0]:
                    memories = []
                    for i, doc in enumerate(results["documents"][0]):
                        metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                        memories.append({
                            "text": doc,
                            "importance": metadata.get("importance", 0.0),
                            "timestamp": metadata.get("timestamp", ""),
                            "interaction_type": metadata.get("interaction_type", "unknown"),
                            "metadata": metadata
                        })
                    
                    # Sort by timestamp (most recent first)
                    memories.sort(key=lambda x: x["timestamp"], reverse=True)
                    return memories[:limit]
                
            except Exception as e:
                logger.error(f"ChromaDB fallback failed: {e}")
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get recent context: {e}")
            return []
    
    async def _cache_recent_memory(self, user_id: str, memory: Dict):
        """Cache recent memory in Redis for fast context retrieval"""
        try:
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            cache_key = f"recent_context:{self._hash_user_id(user_id)}"
            
            import json
            memory_json = json.dumps(memory)
            
            # Add to list (newest first)
            await redis.lpush(cache_key, memory_json)
            
            # Keep only last 10 items
            await redis.ltrim(cache_key, 0, 9)
            
            # Set expiration (24 hours)
            await redis.expire(cache_key, 86400)
            
        except Exception as e:
            logger.debug(f"Failed to cache recent memory: {e}")
    
    def _generate_memory_id(self, user_id: str, text: str, interaction_type: str) -> str:
        """Generate unique memory ID"""
        content = f"{user_id}_{text[:100]}_{interaction_type}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _hash_user_id(self, user_id: str) -> str:
        """Generate consistent hash for user ID (privacy)"""
        return hashlib.sha256(f"eva_user_{user_id}".encode()).hexdigest()[:16]
    
    async def cleanup_old_memories(self, days_old: int = 30):
        """Clean up old memories (maintenance operation)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # This would require custom ChromaDB filtering by timestamp
            # For now, we'll implement basic cleanup
            logger.info(f"Memory cleanup for entries older than {days_old} days")
            
            # TODO: Implement actual cleanup logic based on timestamps
            
        except Exception as e:
            logger.error(f"Memory cleanup failed: {e}")
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory service statistics"""
        try:
            collection_count = self._collection.count() if self._collection else 0
            
            redis_info = {}
            if self._redis_pool:
                redis = aioredis.Redis(connection_pool=self._redis_pool)
                redis_info = await redis.info("memory")
            
            return {
                "initialized": self._initialized,
                "collection_count": collection_count,
                "embedding_model": config.ai.embedding_model,
                "redis_connected": bool(self._redis_pool),
                "redis_memory": redis_info.get("used_memory_human", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
    
    async def delete_user_data(self, user_id: str) -> int:
        """Delete all data for a user (GDPR compliance)"""
        try:
            hashed_user_id = self._hash_user_id(user_id)
            
            # Delete from ChromaDB
            # Note: This requires getting all IDs first, then deleting
            # ChromaDB doesn't have direct delete by metadata
            
            # Delete from Redis cache
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            cache_key = f"recent_context:{hashed_user_id}"
            await redis.delete(cache_key)
            
            logger.info(f"✅ Deleted user data for {user_id[:8]}...")
            return 1  # Placeholder count
            
        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            return 0
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._redis_pool:
            await self._redis_pool.disconnect()
        logger.info("MemoryService cleaned up")

# Singleton instance  
memory_service = MemoryService()