"""人格系统（M23）。

persona traits：humor, curiosity, mischief, honesty, formality。
人格影响回复风格，长期记忆维持人格连贯。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 5 维人格向量
PERSONALITY_DIMS = ["humor", "curiosity", "mischief", "honesty", "formality"]


@dataclass
class Personality:
    """人格特质：5 维向量，每维 0-1。"""

    humor: float = 0.5
    curiosity: float = 0.6
    mischief: float = 0.3
    honesty: float = 0.8
    formality: float = 0.4

    def to_prompt(self) -> str:
        """生成人格描述注入 system prompt。"""
        traits = []
        if self.humor > 0.6:
            traits.append("幽默风趣")
        if self.curiosity > 0.6:
            traits.append("好奇心强")
        if self.mischief > 0.6:
            traits.append("有点调皮")
        if self.honesty > 0.6:
            traits.append("诚实坦率")
        if self.formality > 0.6:
            traits.append("说话正式")
        if not traits:
            return ""
        return f"人格特质：{'、'.join(traits)}"

    def to_dict(self) -> dict:
        return {d: getattr(self, d) for d in PERSONALITY_DIMS}


# 默认人格（玲）
_DEFAULT = Personality(
    humor=0.5,
    curiosity=0.7,
    mischief=0.3,
    honesty=0.8,
    formality=0.3,
)

_personality: Personality | None = None


def get_personality() -> Personality:
    global _personality
    if _personality is None:
        _personality = Personality(**_DEFAULT.to_dict())
    return _personality


def set_personality(p: Personality) -> None:
    global _personality
    _personality = p
