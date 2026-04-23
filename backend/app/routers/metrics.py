"""Prometheus metrics 端点（M14）。

GET /metrics — 返回 Prometheus 格式的指标数据。
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

router = APIRouter(tags=["metrics"])

# 定义指标
REQUEST_COUNT = Counter(
    "webling_requests_total",
    "Total request count",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "webling_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

WS_CONNECTIONS = Counter(
    "webling_ws_connections_total",
    "Total WebSocket connections",
)

TTS_LATENCY = Histogram(
    "webling_tts_duration_seconds",
    "TTS synthesis latency in seconds",
    ["provider"],
)


@router.get("/metrics")
async def metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
