"""互动小游戏 API（M30）。

提供猜谜和问答小游戏。
"""

from __future__ import annotations

import random

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/games", tags=["games"])

RIDDLES = [
    {"q": "什么东西越洗越脏？", "a": "水"},
    {"q": "什么路最窄？", "a": "冤家路窄"},
    {"q": "什么门永远关不上？", "a": "球门"},
    {"q": "什么船最安全？", "a": "停在港湾里的船"},
    {"q": "什么水永远取之不尽？", "a": "口水"},
]

QUIZ = [
    {"q": "Python 是哪一年发布的？", "options": ["1989", "1991", "1995", "2000"], "a": 1},
    {"q": "HTTP 默认端口是？", "options": ["21", "25", "80", "443"], "a": 2},
    {"q": "地球到太阳的距离约是？", "options": ["1.5亿公里", "3亿公里", "5亿公里", "10亿公里"], "a": 0},
    {"q": "世界上最大的海洋是？", "options": ["大西洋", "印度洋", "北冰洋", "太平洋"], "a": 3},
    {"q": "光速约是每秒多少公里？", "options": ["10万", "20万", "30万", "40万"], "a": 2},
]


class RiddleResponse(BaseModel):
    question: str
    answer: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    index: int


class QuizAnswer(BaseModel):
    index: int
    answer: int


class QuizResult(BaseModel):
    correct: bool
    correct_answer: str


@router.get("/riddle", response_model=RiddleResponse)
async def get_riddle() -> RiddleResponse:
    r = random.choice(RIDDLES)
    return RiddleResponse(question=r["q"], answer=r["a"])


@router.get("/quiz", response_model=QuizQuestion)
async def get_quiz() -> QuizQuestion:
    q = random.choice(QUIZ)
    idx = QUIZ.index(q)
    return QuizQuestion(question=q["question"], options=q["options"], index=idx)


@router.post("/quiz/check", response_model=QuizResult)
async def check_quiz(body: QuizAnswer) -> QuizResult:
    if body.index < 0 or body.index >= len(QUIZ):
        return QuizResult(correct=False, correct_answer="无效题目")
    q = QUIZ[body.index]
    correct = body.answer == q["a"]
    return QuizResult(correct=correct, correct_answer=q["options"][q["a"]])
