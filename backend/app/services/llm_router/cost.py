"""
Cost Tracking

Track and estimate LLM costs per tenant.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

from .registry import ModelInfo

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    """Estimated cost for a request."""
    model_id: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"


@dataclass
class UsageRecord:
    """Record of model usage."""
    timestamp: datetime
    model_id: str
    tenant_id: str
    user_id: str
    input_tokens: int
    output_tokens: int
    cost: float
    request_id: str = ""
    task_type: str = ""
    cached: bool = False


class CostTracker:
    """
    Track LLM costs per tenant and user.
    
    Features:
    - Cost estimation
    - Usage tracking
    - Budget limits
    - Cost reports
    """
    
    def __init__(self, storage: Optional[Any] = None):
        self.storage = storage
        self._usage: List[UsageRecord] = []
        self._budgets: Dict[str, float] = {}  # tenant_id -> budget
    
    def estimate(
        self,
        model: ModelInfo,
        input_tokens: int,
        expected_output_tokens: int,
    ) -> CostEstimate:
        """Estimate cost for a request."""
        if not model.pricing:
            return CostEstimate(
                model_id=model.id,
                input_tokens=input_tokens,
                output_tokens=expected_output_tokens,
                input_cost=0.0,
                output_cost=0.0,
                total_cost=0.0,
            )
        
        input_cost = (input_tokens / 1000) * model.pricing.input_cost_per_1k
        output_cost = (expected_output_tokens / 1000) * model.pricing.output_cost_per_1k
        
        return CostEstimate(
            model_id=model.id,
            input_tokens=input_tokens,
            output_tokens=expected_output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            currency=model.pricing.currency,
        )
    
    async def record(
        self,
        model: ModelInfo,
        tenant_id: str,
        user_id: str,
        input_tokens: int,
        output_tokens: int,
        request_id: str = "",
        task_type: str = "",
        cached: bool = False,
    ) -> UsageRecord:
        """Record actual usage."""
        cost = 0.0
        if model.pricing and not cached:
            cost = (
                (input_tokens / 1000) * model.pricing.input_cost_per_1k +
                (output_tokens / 1000) * model.pricing.output_cost_per_1k
            )
        
        record = UsageRecord(
            timestamp=datetime.utcnow(),
            model_id=model.id,
            tenant_id=tenant_id,
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            request_id=request_id,
            task_type=task_type,
            cached=cached,
        )
        
        self._usage.append(record)
        
        # Persist if storage available
        if self.storage:
            try:
                await self.storage.save_usage(record)
            except Exception as e:
                logger.warning(f"Failed to persist usage: {e}")
        
        return record
    
    def set_budget(self, tenant_id: str, budget: float) -> None:
        """Set monthly budget for a tenant."""
        self._budgets[tenant_id] = budget
    
    def check_budget(self, tenant_id: str) -> Dict[str, Any]:
        """Check budget status for a tenant."""
        budget = self._budgets.get(tenant_id)
        if budget is None:
            return {"has_budget": False}
        
        # Calculate current month usage
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        month_cost = sum(
            r.cost for r in self._usage
            if r.tenant_id == tenant_id and r.timestamp >= month_start
        )
        
        return {
            "has_budget": True,
            "budget": budget,
            "used": month_cost,
            "remaining": budget - month_cost,
            "percentage_used": (month_cost / budget) * 100 if budget > 0 else 0,
            "over_budget": month_cost > budget,
        }
    
    def get_usage_report(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage report for a tenant."""
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()
        
        records = [
            r for r in self._usage
            if r.tenant_id == tenant_id
            and start_date <= r.timestamp <= end_date
        ]
        
        # Aggregate by model
        by_model: Dict[str, Dict[str, Any]] = {}
        for r in records:
            if r.model_id not in by_model:
                by_model[r.model_id] = {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "cached_requests": 0,
                }
            by_model[r.model_id]["requests"] += 1
            by_model[r.model_id]["input_tokens"] += r.input_tokens
            by_model[r.model_id]["output_tokens"] += r.output_tokens
            by_model[r.model_id]["cost"] += r.cost
            if r.cached:
                by_model[r.model_id]["cached_requests"] += 1
        
        # Aggregate by user
        by_user: Dict[str, Dict[str, Any]] = {}
        for r in records:
            if r.user_id not in by_user:
                by_user[r.user_id] = {
                    "requests": 0,
                    "cost": 0.0,
                }
            by_user[r.user_id]["requests"] += 1
            by_user[r.user_id]["cost"] += r.cost
        
        # Aggregate by task type
        by_task: Dict[str, Dict[str, Any]] = {}
        for r in records:
            task = r.task_type or "unknown"
            if task not in by_task:
                by_task[task] = {
                    "requests": 0,
                    "cost": 0.0,
                }
            by_task[task]["requests"] += 1
            by_task[task]["cost"] += r.cost
        
        total_cost = sum(r.cost for r in records)
        total_tokens = sum(r.input_tokens + r.output_tokens for r in records)
        cache_hits = sum(1 for r in records if r.cached)
        
        return {
            "tenant_id": tenant_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_requests": len(records),
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "cache_hits": cache_hits,
                "cache_hit_rate": cache_hits / len(records) if records else 0,
            },
            "by_model": by_model,
            "by_user": by_user,
            "by_task": by_task,
        }
    
    def get_daily_costs(
        self,
        tenant_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily cost breakdown."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Group by date
        by_date: Dict[str, float] = {}
        for r in self._usage:
            if r.tenant_id != tenant_id:
                continue
            if r.timestamp < start_date:
                continue
            
            date_str = r.timestamp.strftime("%Y-%m-%d")
            by_date[date_str] = by_date.get(date_str, 0) + r.cost
        
        # Fill in missing dates
        result = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            result.append({
                "date": date_str,
                "cost": by_date.get(date_str, 0),
            })
            current += timedelta(days=1)
        
        return result
