"""wav2vec2 CTC forced alignment，给定 wav + 中文文本，输出字符级时间轴 + viseme。

设计目标：
- TTS 生成一段 wav + 已知文本后，调 ChineseForcedAligner.align(wav_bytes, text) 得到
  ``[{char, t_start, t_end, viseme}, ...]``，供前端驱动 Live2D 嘴型
- 精度目标 ~20-30ms（wav2vec2 CTC 路径本身精度）
- 失败全静默：模型加载不到、文本完全 OOV、forced_align 报错 → 返回空列表，前端
  降级到纯音量驱动嘴型

注：wav2vec2-xlsr-chinese 模型在 CPU 上也能跑，但 GPU（RTX A6000）下单段 100-300ms；
我们部署在 192.168.251.56，跟 TTS 共用 GPU 0，总开销约占 TTS 生成时间的 1/10。
"""

from __future__ import annotations

import io
import logging
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# 中文 wav2vec2-xlsr checkpoint：社区常用 fine-tuned 版本，char-level 输出
_MODEL_ID = "jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn"


# pinyin final → viseme 类别。5 种基础嘴型 + rest
# A=张口宽, O=圆唇, U=撮口, I=扁嘴, E=半开
_VISEME_MAP = {
    # a 系
    "a": "A", "ia": "A", "ua": "A",
    "an": "A", "ang": "A", "ian": "A", "iang": "A", "uan": "A", "uang": "A",
    # o 系
    "o": "O", "uo": "O", "ou": "O", "ao": "O", "iao": "O", "ong": "O", "iong": "O",
    # u 系
    "u": "U", "iu": "U", "un": "U", "ui": "U", "v": "U", "ve": "U",
    # i 系
    "i": "I", "ai": "I", "ei": "I", "in": "I", "ing": "I",
    "ie": "I", "uai": "I", "uei": "I",
    # e 系
    "e": "E", "en": "E", "eng": "E", "er": "E", "ue": "E", "uen": "E",
}

_INITIALS = (
    "zh", "ch", "sh",  # 双字母声母优先匹配
    "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w",
)


def pinyin_to_viseme(pinyin_toneless: str) -> str:
    """pinyin（去声调）→ 嘴型 viseme 标签。
    纯声母 / 未知 → 'rest'。
    """
    if not pinyin_toneless:
        return "rest"
    # 剥掉声母找 final
    final = pinyin_toneless
    for init in _INITIALS:
        if pinyin_toneless.startswith(init):
            final = pinyin_toneless[len(init):]
            break
    if not final:
        return "rest"
    # 先查完整 final，查不到退化到首字母匹配
    if final in _VISEME_MAP:
        return _VISEME_MAP[final]
    for prefix_len in (3, 2, 1):
        key = final[:prefix_len]
        if key in _VISEME_MAP:
            return _VISEME_MAP[key]
    return "rest"


def char_to_viseme(ch: str) -> str:
    """单个字符 → viseme。非中文字符走简单规则。"""
    if not ch.strip():
        return "rest"
    # 英文字母粗略按读音：a/e/i/o/u 对应元音嘴型，其他视为 rest
    if ch.isascii():
        low = ch.lower()
        if low in "a":
            return "A"
        if low in "eh":
            return "E"
        if low in "io":
            return "I"
        if low in "ou":
            return "O"
        if low in "uw":
            return "U"
        return "rest"
    # 中文：查 pypinyin
    try:
        from pypinyin import Style, pinyin  # lazy import
    except ImportError:
        return "rest"
    try:
        py = pinyin(ch, style=Style.NORMAL, heteronym=False, errors="ignore")
    except Exception:
        return "rest"
    if not py or not py[0]:
        return "rest"
    return pinyin_to_viseme(py[0][0])


@dataclass
class TimelineItem:
    char: str
    t_start: float  # 秒
    t_end: float
    viseme: str  # "A" | "O" | "I" | "E" | "U" | "rest"

    def to_dict(self) -> dict[str, Any]:
        return {
            "char": self.char,
            "t_start": round(self.t_start, 3),
            "t_end": round(self.t_end, 3),
            "viseme": self.viseme,
        }


class ChineseForcedAligner:
    """wav2vec2 CTC 强制对齐：单例式加载模型到 GPU，线程安全。"""

    def __init__(self, model_id: str = _MODEL_ID, device: str | None = None) -> None:
        self._model_id = model_id
        self._device = device
        self._model: Any = None
        self._processor: Any = None
        self._tokenizer: Any = None
        self._load_lock = threading.Lock()
        self._load_attempted = False
        self._load_error: str | None = None

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        with self._load_lock:
            if self._load_attempted:
                return
            self._load_attempted = True
            try:
                import torch
                from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            except Exception as exc:
                self._load_error = f"deps missing: {exc}"
                logger.warning("Aligner: %s", self._load_error)
                return
            try:
                logger.warning("[Aligner] 加载 %s ...", self._model_id)
                self._processor = Wav2Vec2Processor.from_pretrained(self._model_id)
                self._tokenizer = self._processor.tokenizer
                self._model = Wav2Vec2ForCTC.from_pretrained(self._model_id)
                if self._device is None:
                    self._device = "cuda" if torch.cuda.is_available() else "cpu"
                self._model.to(self._device)
                self._model.eval()
                logger.warning("[Aligner] 就绪 device=%s", self._device)
            except Exception as exc:
                self._load_error = f"model load failed: {exc}"
                logger.exception("[Aligner] 加载失败")
                self._model = None

    def align(self, wav_bytes: bytes, text: str) -> list[TimelineItem]:
        """给定 wav 字节流 + 原文（中文），返回字符级时间轴。失败返回空 list。"""
        self._ensure_loaded()
        if self._model is None or not text.strip():
            return []
        try:
            return self._align_inner(wav_bytes, text)
        except Exception as exc:
            logger.warning("[Aligner] align failed: %s", exc)
            return []

    def _align_inner(self, wav_bytes: bytes, text: str) -> list[TimelineItem]:
        import numpy as np
        import soundfile as sf
        import torch
        import torchaudio

        # 1. 解码 wav → mono 16k float32
        data, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != 16000:
            data_t = torch.from_numpy(data).unsqueeze(0)
            data = torchaudio.functional.resample(data_t, sr, 16000).squeeze(0).numpy()
            sr = 16000

        # 2. 抽文本里的可对齐字符（中文 + 英文字母；标点跳过）
        chars = [c for c in text if _is_alignable(c)]
        if not chars:
            return []

        # 3. 把字符转 token id；OOV 用 unk_id 占位但后面标 viseme='rest'
        unk_id = self._tokenizer.unk_token_id
        vocab = self._tokenizer.get_vocab()
        token_ids: list[int] = []
        char_valid: list[bool] = []
        for c in chars:
            tid = vocab.get(c, unk_id)
            token_ids.append(tid)
            char_valid.append(tid != unk_id)
        targets = torch.tensor([token_ids], dtype=torch.int32, device=self._device)

        # 4. forward 拿 log-probs
        waveform = torch.from_numpy(data).unsqueeze(0).to(self._device)
        with torch.no_grad():
            logits = self._model(waveform).logits  # (1, T, V)
            log_probs = torch.nn.functional.log_softmax(logits, dim=-1)

        blank_id = self._tokenizer.pad_token_id or 0

        # 5. torchaudio.functional.forced_align（2.1+ 可用）
        alignments, _scores = torchaudio.functional.forced_align(
            log_probs,
            targets,
            blank=blank_id,
        )
        alignments = alignments[0].detach().cpu().tolist()  # 长度 T，每个 frame 的 token idx

        # 6. frame → 秒。wav2vec2 输出帧率：16000 / 320 = 50Hz（官方 conv stride）
        frame_duration = data.shape[0] / sr / max(len(alignments), 1)

        # 7. 把 alignment path 按 target 索引压缩：连续相同 token 记为一段
        spans: list[tuple[int, int, int]] = []  # (token_idx_in_targets, frame_start, frame_end)
        prev_tid = None
        seg_start = 0
        current_target_idx = -1
        for frame_i, tid in enumerate(alignments):
            if tid == blank_id:
                # blank 不算进 target span，但我们把它归给最近的非 blank token
                continue
            if tid != prev_tid:
                # 新 target token
                if prev_tid is not None and current_target_idx >= 0:
                    spans.append((current_target_idx, seg_start, frame_i))
                current_target_idx += 1
                seg_start = frame_i
                prev_tid = tid
        if prev_tid is not None and current_target_idx >= 0:
            spans.append((current_target_idx, seg_start, len(alignments)))

        # 8. 构造 TimelineItem
        items: list[TimelineItem] = []
        for ti, fs, fe in spans:
            if ti >= len(chars):
                continue
            ch = chars[ti]
            t_start = fs * frame_duration
            t_end = fe * frame_duration
            viseme = char_to_viseme(ch) if char_valid[ti] else "rest"
            items.append(TimelineItem(char=ch, t_start=t_start, t_end=t_end, viseme=viseme))
        return items


def _is_alignable(c: str) -> bool:
    """只对齐汉字/英文字母，跳过标点/空白/数字。"""
    if "一" <= c <= "鿿":  # 基本汉字区
        return True
    if c.isalpha():
        return True
    return False


# 单例
_singleton: ChineseForcedAligner | None = None


def get_aligner() -> ChineseForcedAligner:
    global _singleton
    if _singleton is None:
        _singleton = ChineseForcedAligner()
    return _singleton


__all__ = [
    "ChineseForcedAligner",
    "TimelineItem",
    "char_to_viseme",
    "get_aligner",
    "pinyin_to_viseme",
]
