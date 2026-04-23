"""卡拉OK API（M29）。

LRC 歌词解析 + 滚动高亮。
"""

from __future__ import annotations

import re

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/karaoke", tags=["karaoke"])


class LyricLine(BaseModel):
    time: float  # 秒
    text: str


class Song(BaseModel):
    title: str
    artist: str
    lyrics: list[LyricLine]


# 示例歌曲
DEMO_SONG = Song(
    title="小星星",
    artist="经典儿歌",
    lyrics=[
        LyricLine(time=0.0, text="一闪一闪亮晶晶"),
        LyricLine(time=3.0, text="满天都是小星星"),
        LyricLine(time=6.0, text="挂在天空放光明"),
        LyricLine(time=9.0, text="好像许多小眼睛"),
    ],
)


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    """解析 LRC 格式歌词。"""
    lines = []
    for match in re.finditer(r"\[(\d+):(\d+\.\d+)\](.*)", lrc_text):
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        text = match.group(3).strip()
        if text:
            lines.append(LyricLine(time=minutes * 60 + seconds, text=text))
    return sorted(lines, key=lambda l: l.time)


@router.get("/songs", response_model=list[dict])
async def list_songs() -> list[dict]:
    return [{"title": DEMO_SONG.title, "artist": DEMO_SONG.artist}]


@router.get("/songs/demo", response_model=Song)
async def get_demo_song() -> Song:
    return DEMO_SONG
