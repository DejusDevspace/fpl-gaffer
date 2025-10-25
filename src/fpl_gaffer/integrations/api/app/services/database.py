from fpl_gaffer.integrations.api.app.services.supabase import supabase_client
from typing import Optional, List, Dict, Any
from datetime import datetime
from fpl_gaffer.integrations.api.app.utils.logger import logger
from uuid import UUID


class DatabaseService:
    """Service for all database operations using Supabase."""

    def __init__(self):
        self.client = supabase_client.client

    async def create_request(
        self,
        user_id: Optional[str],
        route: str,
        prompt: str,
        response: Optional[str],
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        latency_ms: float,
        model: str,
        status: str = "ok",
        tool_used: Optional[str] = None,
    ) -> Optional[str]:
        """Create a request record."""
        try:
            data = {
                "user_id": user_id,
                "route": route,
                "prompt": prompt,
                "response": response,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
                "model": model,
                "status": status,
                "tool_used": tool_used,
            }

            result = self.client.table("requests").insert(data).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error creating request: {str(e)}")
            return None

    async def create_tool_usage(
        self,
        request_id: str,
        tool_name: str,
        duration_ms: float,
    ) -> bool:
        """Record per-tool execution duration."""
        try:
            data = {
                "request_id": request_id,
                "tool_name": tool_name,
                "duration_ms": duration_ms,
            }

            self.client.table("tools_usage").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating tool usage: {str(e)}")
            return False

    async def get_metrics_summary(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Get aggregated metrics using Supabase RPC or direct queries."""
        try:
            # Query requests within date range
            response = self.client.table("requests") \
                .select("tokens_in, tokens_out, cost_usd, latency_ms, status") \
                .gte("created_at", start_date.isoformat()) \
                .lte("created_at", end_date.isoformat()) \
                .execute()

            requests = response.data

            if not requests:
                return {
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "avg_latency_ms": 0.0,
                    "total_requests": 0,
                    "error_rate": 0.0,
                }

            total_tokens = sum(r["tokens_in"] + r["tokens_out"] for r in requests)
            total_cost = sum(r["cost_usd"] for r in requests)
            avg_latency = sum(r["latency_ms"] for r in requests) / len(requests)
            total_requests = len(requests)
            error_count = sum(1 for r in requests if r["status"] == "error")
            error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "total_tokens": total_tokens,
                "total_cost_usd": float(total_cost),
                "avg_latency_ms": float(avg_latency),
                "total_requests": total_requests,
                "error_rate": error_rate,
            }
        except Exception as e:
            logger.error(f"Error getting metrics summary: {str(e)}")
            return {
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "total_requests": 0,
                "error_rate": 0.0,
            }

    async def get_timeseries(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get timeseries data (tokens/day, cost/day)."""
        try:
            response = self.client.table("requests") \
                .select("created_at, tokens_in, tokens_out, cost_usd, latency_ms") \
                .gte("created_at", start_date.isoformat()) \
                .lte("created_at", end_date.isoformat()) \
                .order("created_at") \
                .execute()

            requests = response.data

            # Group by date
            daily_data = {}
            for req in requests:
                date = req["created_at"].split("T")[0]
                if date not in daily_data:
                    daily_data[date] = {
                        "tokens": 0,
                        "cost_usd": 0.0,
                        "latencies": [],
                        "count": 0,
                    }

                daily_data[date]["tokens"] += req["tokens_in"] + req["tokens_out"]
                daily_data[date]["cost_usd"] += req["cost_usd"]
                daily_data[date]["latencies"].append(req["latency_ms"])
                daily_data[date]["count"] += 1

            # Format results
            result = []
            for date, data in sorted(daily_data.items()):
                avg_latency = sum(data["latencies"]) / len(data["latencies"]) if data["latencies"] else 0
                result.append({
                    "date": date,
                    "tokens": data["tokens"],
                    "cost_usd": float(data["cost_usd"]),
                    "avg_latency_ms": float(avg_latency),
                    "request_count": data["count"],
                })

            return result
        except Exception as e:
            logger.error(f"Error getting timeseries: {str(e)}")
            return []

    async def get_requests(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get paginated requests with filters."""
        try:
            query = self.client.table("requests").select("*")

            if user_id:
                query = query.eq("user_id", user_id)

            if status:
                query = query.eq("status", status)

            response = query.order("created_at", desc=True) \
                .limit(limit) \
                .offset(offset) \
                .execute()

            return response.data or []
        except Exception as e:
            logger.error(f"Error getting requests: {str(e)}")
            return []

    async def get_users(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get all users with usage stats."""
        try:
            users_response = self.client.table("users") \
                .select("*") \
                .limit(limit) \
                .offset(offset) \
                .execute()

            users = users_response.data or []

            # Get usage stats for each user
            for user in users:
                requests_response = self.client.table("requests") \
                    .select("tokens_in, tokens_out, cost_usd") \
                    .eq("user_id", user["id"]) \
                    .execute()

                requests = requests_response.data or []
                user["request_count"] = len(requests)
                user["total_tokens"] = sum(r["tokens_in"] + r["tokens_out"] for r in requests)
                user["total_cost_usd"] = sum(r["cost_usd"] for r in requests)

            return users
        except Exception as e:
            logger.error(f"Error getting users: {str(e)}")
            return []


database_service = DatabaseService()
