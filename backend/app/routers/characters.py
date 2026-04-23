"""Character API 路由（M7）。

GET /api/characters       — 查询所有角色
GET /api/characters/{id}  — 查询单个角色
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.schemas.character import CharacterInfo, CharacterList

router = APIRouter(tags=["characters"])


def _doc_to_info(doc: dict) -> CharacterInfo:
    doc.pop("_id", None)
    return CharacterInfo(**doc)


@router.get("/characters", response_model=CharacterList)
async def list_characters(request: Request) -> CharacterList:
    db = getattr(request.app.state, "db", None)
    if db is None:
        return CharacterList(characters=[])
    cursor = db.characters.find({"enabled": True})
    docs = await cursor.to_list(length=100)
    return CharacterList(characters=[_doc_to_info(d) for d in docs])


@router.get("/characters/{character_id}", response_model=CharacterInfo)
async def get_character(character_id: str, request: Request) -> CharacterInfo:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=404, detail="character not found (no db)")
    doc = await db.characters.find_one({"id": character_id})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"character not found: {character_id}")
    return _doc_to_info(doc)
