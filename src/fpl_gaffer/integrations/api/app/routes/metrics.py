import datetime as dt
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

# from fpl_gaffer.integrations.api.app.db import get_db
from fpl_gaffer.integrations.api.app.services.database import database_service

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


class MetricsSummary(BaseModel):
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    total_requests: int
    error_rate: float


class TimeseriesPoint(BaseModel):
    date: str
    tokens: int
    cost_usd: float
    avg_latency_ms: float
    request_count: int


class RequestDetail(BaseModel):
    id: str
    user_id: Optional[str]
    route: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    status: str
    model: str
    tool_used: Optional[str]
    created_at: str


@router.get("/summary", response_model=MetricsSummary)
async def get_summary(
    start: str = Query("2024-01-01"),  # Placeholder, would change
    end: str = Query(None),
):
    """Get aggregated metrics for date range."""
    start_date = datetime.fromisoformat(start)
    end_date = datetime.fromisoformat(end) if end else datetime.now(dt.timezone.utc)

    summary = await database_service.get_metrics_summary(start_date, end_date)
    return MetricsSummary(**summary)


@router.get("/timeseries", response_model=List[TimeseriesPoint])
async def get_timeseries(
    start: str = Query("2024-01-01"),  # Placeholder, would change
    end: str = Query(None),
):
    """Get timeseries metrics (tokens/day, cost/day)."""
    start_date = datetime.fromisoformat(start)
    end_date = datetime.fromisoformat(end) if end else datetime.now(dt.timezone.utc)

    timeseries = await database_service.get_timeseries(start_date, end_date)
    return [TimeseriesPoint(**item) for item in timeseries]


@router.get("/requests", response_model=List[RequestDetail])
async def get_requests(
    limit: int = Query(100),
    offset: int = Query(0),
    status: Optional[str] = Query(None),
):
    """Get paginated requests with filters."""
    requests = await database_service.get_requests(limit=limit, offset=offset, status=status)
    return [RequestDetail(**r) for r in requests]
