"""知识图谱 API（M31）。

提供知识图谱的查询接口。
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


class KGNode(BaseModel):
    id: str
    label: str
    type: str


class KGEdge(BaseModel):
    source: str
    target: str
    label: str


class KGGraph(BaseModel):
    nodes: list[KGNode]
    edges: list[KGEdge]


# 示例数据
_DEMO_GRAPH = KGGraph(
    nodes=[
        KGNode(id="ling", label="玲", type="character"),
        KGNode(id="tts", label="TTS", type="technology"),
        KGNode(id="live2d", label="Live2D", type="technology"),
        KGNode(id="cosyvoice", label="CosyVoice", type="provider"),
        KGNode(id="edge-tts", label="Edge TTS", type="provider"),
        KGNode(id="mongodb", label="MongoDB", type="database"),
        KGNode(id="fastapi", label="FastAPI", type="framework"),
        KGNode(id="vue", label="Vue 3", type="framework"),
    ],
    edges=[
        KGEdge(source="ling", target="tts", label="使用"),
        KGEdge(source="ling", target="live2d", label="显示形象"),
        KGEdge(source="tts", target="cosyvoice", label="支持"),
        KGEdge(source="tts", target="edge-tts", label="支持"),
        KGEdge(source="ling", target="mongodb", label="存储"),
        KGEdge(source="ling", target="fastapi", label="后端"),
        KGEdge(source="ling", target="vue", label="前端"),
    ],
)


@router.get("", response_model=KGGraph)
async def get_graph() -> KGGraph:
    return _DEMO_GRAPH
