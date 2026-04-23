"""Prompt 模板管理（M21）。

支持 Jinja2 模板 + Mongo 版本存储。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptTemplate(BaseModel):
    id: str
    name: str
    template: str
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PromptListResponse(BaseModel):
    prompts: list[PromptTemplate]


class PromptCreateRequest(BaseModel):
    id: str
    name: str
    template: str


class PromptUpdateRequest(BaseModel):
    template: str


def _get_db(request: Request):
    return getattr(request.app.state, "db", None)


@router.get("", response_model=PromptListResponse)
async def list_prompts(request: Request) -> PromptListResponse:
    db = _get_db(request)
    if db is None:
        return PromptListResponse(prompts=[])
    cursor = db.prompts.find()
    docs = await cursor.to_list(length=100)
    prompts = []
    for doc in docs:
        doc.pop("_id", None)
        prompts.append(PromptTemplate(**doc))
    return PromptListResponse(prompts=prompts)


@router.get("/{prompt_id}", response_model=PromptTemplate)
async def get_prompt(prompt_id: str, request: Request) -> PromptTemplate:
    db = _get_db(request)
    if db is None:
        raise HTTPException(status_code=404, detail="no db")
    doc = await db.prompts.find_one({"id": prompt_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    doc.pop("_id", None)
    return PromptTemplate(**doc)


@router.post("", response_model=PromptTemplate)
async def create_prompt(body: PromptCreateRequest, request: Request) -> PromptTemplate:
    db = _get_db(request)
    if db is None:
        raise HTTPException(status_code=503, detail="no db")
    now = datetime.now(tz=UTC)
    prompt = PromptTemplate(
        id=body.id,
        name=body.name,
        template=body.template,
        version=1,
        created_at=now,
        updated_at=now,
    )
    await db.prompts.insert_one(prompt.model_dump(mode="json"))
    return prompt


@router.put("/{prompt_id}", response_model=PromptTemplate)
async def update_prompt(
    prompt_id: str, body: PromptUpdateRequest, request: Request
) -> PromptTemplate:
    db = _get_db(request)
    if db is None:
        raise HTTPException(status_code=503, detail="no db")
    doc = await db.prompts.find_one({"id": prompt_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="prompt not found")
    now = datetime.now(tz=UTC)
    new_version = doc.get("version", 1) + 1
    await db.prompts.update_one(
        {"id": prompt_id},
        {"$set": {"template": body.template, "version": new_version, "updated_at": now.isoformat()}},
    )
    return PromptTemplate(
        id=prompt_id,
        name=doc["name"],
        template=body.template,
        version=new_version,
        created_at=doc.get("created_at"),
        updated_at=now,
    )
