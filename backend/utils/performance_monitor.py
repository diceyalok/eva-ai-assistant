"""
Performance Monitor - Track response times against PRD targets
≤2.5s text responses, ≤1.2s voice processing
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import redis.asyncio as aioredis
from ..core.config_manager import config

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and optimize performance against PRD targets"""
    
    def __init__(self):
        self._redis_pool = None
        self.targets = {
            "text_response": 2.5,  # seconds
            "voice_processing": 1.2,  # seconds
            "memory_search": 0.5,  # seconds
            "model_inference": 1.5,  # seconds
        }
        
    async def initialize(self):
        """Initialize performance monitoring"""
        try:
            self._redis_pool = aioredis.ConnectionPool.from_url(
                config.database.redis_url,
                decode_responses=True,
                max_connections=5
            )
            logger.info("📊 Performance Monitor initialized")
        except Exception as e:
            logger.error(f"Performance Monitor init failed: {e}")
    
    @asynccontextmanager
    async def track_operation(self, operation: str, target_time: Optional[float] = None):
        """Context manager to track operation performance"""
        start_time = time.time()
        operation_data = {
            "operation": operation,
            "start_time": start_time,
            "target": target_time or self.targets.get(operation, 3.0)
        }
        
        try:
            yield operation_data
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            await self._record_performance(operation, duration, operation_data["target"])
    
    async def _record_performance(self, operation: str, duration: float, target: float):
        """Record performance metrics"""
        try:
            if not self._redis_pool:
                return
                
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            
            # Record individual timing
            await redis.zadd(
                f"perf:{operation}:times",
                {str(int(time.time())): duration}
            )
            
            # Keep only last 1000 measurements
            await redis.zremrangebyrank(f"perf:{operation}:times", 0, -1001)
            
            # Update counters
            status = "pass" if duration <= target else "fail"
            await redis.hincrby(f"perf:{operation}:counts", status, 1)
            
            # Log if exceeding target
            if duration > target:
                logger.warning(f"⚠️ {operation} exceeded target: {duration:.2f}s > {target:.2f}s")
            else:
                logger.debug(f"✅ {operation} within target: {duration:.2f}s ≤ {target:.2f}s")
                
        except Exception as e:
            logger.error(f"Performance recording failed: {e}")
    
    async def get_performance_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get performance statistics"""
        try:
            if not self._redis_pool:
                return {"error": "Performance monitor not initialized"}
                
            redis = aioredis.Redis(connection_pool=self._redis_pool)
            
            if operation:
                return await self._get_operation_stats(redis, operation)
            else:
                # Get stats for all operations
                stats = {}
                for op in self.targets.keys():
                    stats[op] = await self._get_operation_stats(redis, op)
                return stats
                
        except Exception as e:
            logger.error(f"Performance stats failed: {e}")
            return {"error": str(e)}
    
    async def _get_operation_stats(self, redis, operation: str) -> Dict[str, Any]:
        """Get statistics for specific operation"""
        
        # Get recent timings
        recent_times = await redis.zrange(
            f"perf:{operation}:times", -100, -1, withscores=True
        )
        
        # Get pass/fail counts
        counts = await redis.hgetall(f"perf:{operation}:counts")
        
        if not recent_times:
            return {
                "operation": operation,
                "target": self.targets.get(operation, 3.0),
                "sample_count": 0,
                "status": "no_data"
            }
        
        # Calculate statistics
        durations = [float(score) for _, score in recent_times]
        avg_time = sum(durations) / len(durations)
        p95_time = sorted(durations)[int(len(durations) * 0.95)]
        
        total_count = sum(int(counts.get(k, 0)) for k in ["pass", "fail"])
        pass_count = int(counts.get("pass", 0))
        success_rate = (pass_count / total_count * 100) if total_count > 0 else 0
        
        target = self.targets.get(operation, 3.0)
        
        return {
            "operation": operation,
            "target": target,
            "avg_time": round(avg_time, 3),
            "p95_time": round(p95_time, 3),
            "sample_count": len(durations),
            "success_rate": round(success_rate, 1),
            "status": "healthy" if avg_time <= target else "degraded",
            "total_operations": total_count
        }
    
    async def optimize_if_needed(self, operation: str, current_duration: float):
        """Trigger optimizations if performance degrades"""
        target = self.targets.get(operation, 3.0)
        
        if current_duration > target * 1.5:  # 50% over target
            logger.warning(f"🚨 Performance critical for {operation}: {current_duration:.2f}s")
            await self._trigger_optimization(operation)
    
    async def _trigger_optimization(self, operation: str):
        """Trigger specific optimizations based on operation"""
        
        optimizations = {
            "text_response": self._optimize_text_processing,
            "voice_processing": self._optimize_voice_processing,
            "memory_search": self._optimize_memory_search,
            "model_inference": self._optimize_model_inference
        }
        
        if operation in optimizations:
            try:
                await optimizations[operation]()
                logger.info(f"🔧 Optimization triggered for {operation}")
            except Exception as e:
                logger.error(f"Optimization failed for {operation}: {e}")
    
    async def _optimize_text_processing(self):
        """Optimize text response processing"""
        # Clear old caches, warm up models, adjust batch sizes
        from ..core.model_manager import model_manager
        await model_manager.optimize_for_speed()
    
    async def _optimize_voice_processing(self):
        """Optimize voice processing pipeline"""
        # Reduce audio processing quality temporarily, clear voice caches
        from ..core.voice_service import voice_service
        await voice_service.clear_cache("*")
    
    async def _optimize_memory_search(self):
        """Optimize memory search performance"""
        # Reduce search depth, clear old embeddings cache
        from ..core.memory_service import memory_service
        await memory_service.optimize_search_performance()
    
    async def _optimize_model_inference(self):
        """Optimize model inference speed"""
        # Adjust batch sizes, clear model caches
        from ..core.model_manager import model_manager
        await model_manager.clear_embedding_cache()

# Global instance
performance_monitor = PerformanceMonitor()