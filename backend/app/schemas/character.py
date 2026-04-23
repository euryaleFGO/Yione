"""Character API schemas（M7）。"""

from __future__ import annotations

from pydantic import BaseModel


class CharacterInfo(BaseModel):
    id: str
    name: str
    avatar_config: dict
    greeting: str
    system_prompt: str
    voice_id: str | None = None
    enabled: bool = True


class CharacterList(BaseModel):
    characters: list[CharacterInfo]
