"""技能插件框架 API（M28）。

提供技能注册和调用接口。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])


class Skill(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool = True


class SkillListResponse(BaseModel):
    skills: list[Skill]


class SkillCallRequest(BaseModel):
    skill_id: str
    args: dict = {}


class SkillCallResponse(BaseModel):
    skill_id: str
    result: str


# 示例技能
DEMO_SKILLS = [
    Skill(id="weather", name="天气查询", description="查询指定城市的天气"),
    Skill(id="calendar", name="日历", description="查看和管理日程"),
    Skill(id="notes", name="笔记", description="创建和查询笔记"),
]


@router.get("", response_model=SkillListResponse)
async def list_skills() -> SkillListResponse:
    return SkillListResponse(skills=DEMO_SKILLS)


@router.post("/call", response_model=SkillCallResponse)
async def call_skill(body: SkillCallRequest) -> SkillCallResponse:
    skill = next((s for s in DEMO_SKILLS if s.id == body.skill_id), None)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"技能不存在: {body.skill_id}")

    if body.skill_id == "weather":
        city = body.args.get("city", "北京")
        return SkillCallResponse(skill_id=body.skill_id, result=f"{city}：晴，25°C")
    elif body.skill_id == "calendar":
        return SkillCallResponse(skill_id=body.skill_id, result="今天没有待办事项")
    elif body.skill_id == "notes":
        return SkillCallResponse(skill_id=body.skill_id, result="暂无笔记")
    else:
        return SkillCallResponse(skill_id=body.skill_id, result="技能执行完成")
