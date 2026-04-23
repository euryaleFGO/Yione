"""音频字节流 → SVEngine 能吃的 float32 mono ndarray。

- 尽量走 ``soundfile``（libsndfile），它比 ``wave`` 宽容得多，wav/flac/ogg 都能读。
- 读到的多声道做均值降成 mono。
- 采样率不是 16k 就线性重采样（纯 numpy 实现，轻量；对识别精度影响可以接受）。
- 依赖 numpy/soundfile 是 [sv] optional extra，没装时抛 AudioDecodeError，
  上层走降级路径即可（SpeakerService 返回 engine_available=False）。
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


class AudioDecodeError(Exception):
    """音频解码失败——文件格式坏了或 [sv] 依赖没装。"""


def decode_wav_bytes(data: bytes, *, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """把浏览器/HTTP 上传的 wav bytes 解成 (mono_float32_array, sample_rate)。

    解码失败 → AudioDecodeError。调用方负责捕获并降级。
    """
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise AudioDecodeError(
            f"缺少 [sv] 依赖（numpy/soundfile），无法解码音频: {exc}"
        ) from exc

    try:
        audio, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    except Exception as exc:
        raise AudioDecodeError(f"soundfile 读取失败: {exc}") from exc

    # 多声道降 mono
    if audio.ndim == 2:
        audio = audio.mean(axis=1).astype(np.float32, copy=False)

    if sr != target_sr:
        audio = _resample_linear(audio, sr, target_sr)
        sr = target_sr

    return audio, sr


def _resample_linear(audio: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """最朴素的线性插值重采样。给声纹识别用精度够；ASR 会换 torchaudio。"""
    import numpy as np

    if src_sr == dst_sr:
        return audio
    ratio = dst_sr / src_sr
    new_len = round(len(audio) * ratio)
    if new_len <= 1:
        return np.zeros(0, dtype=np.float32)
    src_idx = np.linspace(0, len(audio) - 1, num=new_len, dtype=np.float64)
    lo = np.floor(src_idx).astype(np.int64)
    hi = np.clip(lo + 1, 0, len(audio) - 1)
    frac = (src_idx - lo).astype(np.float32)
    out = audio[lo] * (1 - frac) + audio[hi] * frac
    return out.astype(np.float32, copy=False)


__all__ = ["AudioDecodeError", "decode_wav_bytes"]
