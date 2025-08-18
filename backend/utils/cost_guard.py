import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import redis.asyncio as aioredis
import logging
import json

logger = logging.getLogger(__name__)


class CostGuard:
    """Cost tracking and limiting for external API calls (GPT-4o)"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        
        # Cost limits in INR
        self.limits = {
            "daily_user": 50.0,      # ₹50 per user per day
            "monthly_user": 500.0,   # ₹500 per user per month
            "daily_global": 5000.0,  # ₹5000 per day globally
            "monthly_global": 20000.0 # ₹20k per month globally
        }
        
        # Token costs in INR (GPT-4o pricing)
        self.token_costs = {
            "gpt-4o": {
                "input": 0.000005,   # ₹0.000005 per input token
                "output": 0.000015   # ₹0.000015 per output token
            },
            "gpt-4o-mini": {
                "input": 0.0000015,  # ₹0.0000015 per input token
                "output": 0.0000006  # ₹0.0000006 per output token
            }
        }
    
    async def check_budget(self, user_id: str, estimated_cost: float = 0.0) -> Tuple[bool, str]:
        """Check if user/system has budget for the request"""
        try:
            current_costs = await self.get_current_costs(user_id)
            
            # Check user daily limit
            if current_costs["user_daily"] + estimated_cost > self.limits["daily_user"]:
                return False, f"Daily limit exceeded (₹{self.limits['daily_user']})"
            
            # Check user monthly limit
            if current_costs["user_monthly"] + estimated_cost > self.limits["monthly_user"]:
                return False, f"Monthly limit exceeded (₹{self.limits['monthly_user']})"
            
            # Check global daily limit
            if current_costs["global_daily"] + estimated_cost > self.limits["daily_global"]:
                return False, f"System daily limit exceeded"
            
            # Check global monthly limit
            if current_costs["global_monthly"] + estimated_cost > self.limits["monthly_global"]:
                return False, f"System monthly limit exceeded"
            
            return True, "Budget available"
            
        except Exception as e:
            logger.error(f"Budget check failed: {e}")
            # Fail safe - deny request if Redis is down
            return False, "Budget check failed"
    
    async def record_usage(self, user_id: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Record API usage and calculate cost"""
        try:
            # Calculate cost
            costs = self.token_costs.get(model, self.token_costs["gpt-4o"])
            total_cost = (input_tokens * costs["input"]) + (output_tokens * costs["output"])
            
            now = datetime.utcnow()
            today = now.strftime("%Y-%m-%d")
            this_month = now.strftime("%Y-%m")
            
            # Redis keys
            user_daily_key = f"cost:user:{user_id}:daily:{today}"
            user_monthly_key = f"cost:user:{user_id}:monthly:{this_month}"
            global_daily_key = f"cost:global:daily:{today}"
            global_monthly_key = f"cost:global:monthly:{this_month}"
            
            # Record usage in Redis
            pipe = self.redis.pipeline()
            
            # Increment costs
            pipe.incrbyfloat(user_daily_key, total_cost)
            pipe.incrbyfloat(user_monthly_key, total_cost)
            pipe.incrbyfloat(global_daily_key, total_cost)
            pipe.incrbyfloat(global_monthly_key, total_cost)
            
            # Set expiration
            pipe.expire(user_daily_key, 86400 * 2)  # 2 days
            pipe.expire(user_monthly_key, 86400 * 35)  # 35 days
            pipe.expire(global_daily_key, 86400 * 2)
            pipe.expire(global_monthly_key, 86400 * 35)
            
            await pipe.execute()
            
            # Log usage
            usage_data = {
                "user_id": user_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_inr": total_cost,
                "timestamp": now.isoformat()
            }
            
            # Store detailed usage log
            await self.redis.lpush(
                f"usage:log:{user_id}",
                json.dumps(usage_data)
            )
            await self.redis.ltrim(f"usage:log:{user_id}", 0, 999)  # Keep last 1000 entries
            
            logger.info(f"Recorded usage: {user_id} | {model} | ₹{total_cost:.4f}")
            return total_cost
            
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            return 0.0
    
    async def get_current_costs(self, user_id: str) -> Dict[str, float]:
        """Get current costs for user and global"""
        try:
            now = datetime.utcnow()
            today = now.strftime("%Y-%m-%d")
            this_month = now.strftime("%Y-%m")
            
            # Redis keys
            keys = [
                f"cost:user:{user_id}:daily:{today}",
                f"cost:user:{user_id}:monthly:{this_month}",
                f"cost:global:daily:{today}",
                f"cost:global:monthly:{this_month}"
            ]
            
            # Get all costs
            costs = await self.redis.mget(keys)
            
            return {
                "user_daily": float(costs[0] or 0),
                "user_monthly": float(costs[1] or 0),
                "global_daily": float(costs[2] or 0),
                "global_monthly": float(costs[3] or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get current costs: {e}")
            return {
                "user_daily": 0.0,
                "user_monthly": 0.0,
                "global_daily": 0.0,
                "global_monthly": 0.0
            }
    
    async def get_usage_stats(self, user_id: str) -> Dict:
        """Get detailed usage statistics for user"""
        try:
            costs = await self.get_current_costs(user_id)
            
            # Get usage history
            usage_logs = await self.redis.lrange(f"usage:log:{user_id}", 0, 99)
            usage_history = []
            
            for log_entry in usage_logs:
                try:
                    usage_history.append(json.loads(log_entry))
                except:
                    continue
            
            return {
                "costs": costs,
                "limits": {
                    "daily": self.limits["daily_user"],
                    "monthly": self.limits["monthly_user"]
                },
                "remaining": {
                    "daily": max(0, self.limits["daily_user"] - costs["user_daily"]),
                    "monthly": max(0, self.limits["monthly_user"] - costs["user_monthly"])
                },
                "usage_history": usage_history[:10]  # Last 10 entries
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {"error": "Failed to retrieve stats"}
    
    async def estimate_cost(self, text: str, model: str = "gpt-4o") -> float:
        """Estimate cost for a given text"""
        try:
            # Rough token estimation (1 token ≈ 4 characters for English)
            estimated_tokens = len(text) // 4
            
            costs = self.token_costs.get(model, self.token_costs["gpt-4o"])
            
            # Assume 1:1 input:output ratio for estimation
            estimated_cost = (estimated_tokens * costs["input"]) + (estimated_tokens * costs["output"])
            
            return estimated_cost
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return 0.01  # Default small cost
    
    async def reset_user_costs(self, user_id: str, admin_user: str):
        """Reset user costs (admin function)"""
        try:
            pattern = f"cost:user:{user_id}:*"
            keys = await self.redis.keys(pattern)
            
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Reset costs for user {user_id} by admin {admin_user}")
            
            # Also clear usage logs
            await self.redis.delete(f"usage:log:{user_id}")
            
        except Exception as e:
            logger.error(f"Failed to reset user costs: {e}")
    
    async def get_global_stats(self) -> Dict:
        """Get global cost statistics (admin function)"""
        try:
            now = datetime.utcnow()
            today = now.strftime("%Y-%m-%d")
            this_month = now.strftime("%Y-%m")
            
            costs = {
                "daily": float(await self.redis.get(f"cost:global:daily:{today}") or 0),
                "monthly": float(await self.redis.get(f"cost:global:monthly:{this_month}") or 0)
            }
            
            return {
                "costs": costs,
                "limits": {
                    "daily": self.limits["daily_global"],
                    "monthly": self.limits["monthly_global"]
                },
                "remaining": {
                    "daily": max(0, self.limits["daily_global"] - costs["daily"]),
                    "monthly": max(0, self.limits["monthly_global"] - costs["monthly"])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get global stats: {e}")
            return {"error": "Failed to retrieve global stats"}