"""Ling SVEngine 的轻量适配层（M16）。

设计原则：

- **懒加载**：不在进程启动时就触发 funasr/torch 导入和模型下载（启动 2-5 秒太慢），
  第一次调 ``embed`` 才真正 import + 实例化。
- **可降级**：依赖没装（webLing 默认 pyproject 没把 torch/funasr 列为硬依赖）
  或模型加载失败时，返回 ``is_available=False``，所有 embed 返回 None。
  SpeakerService 会据此把接口结果的 ``engine_available`` 置 False 返回给前端。
- **fail-open 与 fail-close 的选择**：Ling 的 SVEngine 自身在模型失败时会
  ``fail_open``（verify 一律放行），不适合 webLing 的多说话人识别场景；
  我们在这里改成 ``fail_close``——引擎挂了就不做识别，宁可漏判也不误判。
- **音频接入口**：只接受已经解码成 ``numpy.float32`` mono 的 ``np.ndarray``；
  bytes→ndarray 的活交给上层调用方（services/speaker_service + soundfile）。

Voiceprint 向量：Ling 的 CampPlus 模型会在 embed 时做 L2 归一化，所以对比用
点积即可当作余弦相似度。阈值默认跟 Ling 对齐（0.38）。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.config import get_settings
from app.integrations.ling_adapter import inject_ling_path

if TYPE_CHECKING:
    import numpy as np  # 仅用于类型标注，运行时可能没装

logger = logging.getLogger(__name__)


# 默认阈值对齐 Ling SVEngine（CampPlus 模型，余弦相似度空间）
DEFAULT_THRESHOLD = 0.38
# 向量维度随模型而定；CampPlus zh 16k common 输出 192 维；我们不假设具体维度，
# 以第一次 embed 成功时实测到的长度为准。
_EXPECTED_SAMPLE_RATE = 16000


class SVAdapter:
    """常驻内存的 SVEngine 包装；首次使用时才加载模型。"""

    def __init__(self, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.threshold = threshold
        self._engine: Any = None
        self._load_attempted = False
        self._load_error: str | None = None

    @property
    def is_available(self) -> bool:
        """模型是否可用。首次访问时会触发懒加载。"""
        self._ensure_loaded()
        return self._engine is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        settings = get_settings()
        if inject_ling_path(settings.ling_repo_path) is None:
            self._load_error = f"Ling 仓库不存在: {settings.ling_repo_path}"
            logger.warning("SVAdapter: %s", self._load_error)
            return

        try:
            # 放到方法内部懒加载：torch/funasr 比较重，导入就几百毫秒起步
            from src.core.sv_engine import SVEngine  # type: ignore[import-not-found]
        except Exception as exc:
            self._load_error = f"无法导入 Ling SVEngine: {exc}"
            logger.warning("SVAdapter: %s", self._load_error)
            return

        try:
            # 把阈值传下去，模型 lazy 在第一次 embed 时真正加载
            self._engine = SVEngine(threshold=self.threshold)
            logger.info("SVAdapter: SVEngine 构造完成（模型按需加载）")
        except Exception as exc:
            self._load_error = f"SVEngine 实例化失败: {exc}"
            logger.warning("SVAdapter: %s", self._load_error)
            self._engine = None

    def embed(self, audio: np.ndarray, sample_rate: int = _EXPECTED_SAMPLE_RATE) -> list[float] | None:
        """提取声纹向量，返回 Python list[float]（好序列化，避开 numpy 在上层流转）。

        - 引擎不可用时直接返回 None，调用方自己决定怎么降级。
        - 向量已 L2 归一化，对比用点积当余弦相似度。
        """
        self._ensure_loaded()
        if self._engine is None:
            return None
        try:
            vec = self._engine.embed(audio, sample_rate=sample_rate)
        except Exception as exc:
            logger.warning("SVAdapter.embed 失败: %s", exc)
            return None
        return [float(x) for x in vec]


_singleton: SVAdapter | None = None


def get_sv_adapter() -> SVAdapter:
    global _singleton
    if _singleton is None:
        _singleton = SVAdapter()
    return _singleton


def set_sv_adapter_for_tests(adapter: SVAdapter | None) -> None:
    """仅供测试用：把 singleton 替换掉（避免真的去拉模型）。"""
    global _singleton
    _singleton = adapter


__all__ = [
    "DEFAULT_THRESHOLD",
    "SVAdapter",
    "get_sv_adapter",
    "set_sv_adapter_for_tests",
]
