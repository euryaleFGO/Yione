"""Character 数据模型（M7）。

Character 是全局共享的角色定义，不归 tenant 所有。
Tenant 通过 character_whitelist 控制可用角色。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Character:
    id: str
    name: str
    avatar_config: dict = field(default_factory=dict)
    greeting: str = "你好呀，我是玲。很高兴见到你。"
    system_prompt: str = ""
    voice_id: str | None = None
    enabled: bool = True
