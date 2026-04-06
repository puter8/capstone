# -*- coding: utf-8 -*-
"""
CHARACTER MATRIX 학습 데이터셋
==========================
팀이 직접 채점한 Ground Truth 라벨 데이터.

구조:
  utterance : 영어 발화 원문
  label     : 5축 정답 수치 (Formality, Energy, Intimacy, Humor, Curiosity) 0~100
  style     : 발화 스타일 카테고리 (학습 시 클래스 레이블로 활용)

용도:
  - 현재: 규칙 기반 분석기 검증 (rule vs ground truth 오차 확인)
  - 추후: LLM/ML 모델 파인튜닝용 학습 데이터
"""

DATASET = [

    # ── CASUAL / SLANG ────────────────────────────────────────────────────────
    {
        "utterance": "yo what's up lol, u wanna hang or nah?",
        "label": {"Formality": 5,  "Energy": 70, "Intimacy": 75, "Humor": 60, "Curiosity": 25},
        "style": "casual",
    },
    {
        "utterance": "omg I literally can't even rn 😭😭",
        "label": {"Formality": 5,  "Energy": 85, "Intimacy": 60, "Humor": 70, "Curiosity": 15},
        "style": "casual",
    },
    {
        "utterance": "bruh that's so sus ngl fr fr",
        "label": {"Formality": 5,  "Energy": 65, "Intimacy": 55, "Humor": 75, "Curiosity": 20},
        "style": "casual",
    },
    {
        "utterance": "lmao bestie u okay?? that's wild",
        "label": {"Formality": 5,  "Energy": 75, "Intimacy": 80, "Humor": 65, "Curiosity": 30},
        "style": "casual",
    },
    {
        "utterance": "no cap that movie was bussin, we gotta watch it again",
        "label": {"Formality": 5,  "Energy": 70, "Intimacy": 65, "Humor": 55, "Curiosity": 20},
        "style": "casual",
    },

    # ── FORMAL ───────────────────────────────────────────────────────────────
    {
        "utterance": "I would like to formally inquire about the implications of this matter.",
        "label": {"Formality": 95, "Energy": 20, "Intimacy": 5,  "Humor": 5,  "Curiosity": 65},
        "style": "formal",
    },
    {
        "utterance": "Please be advised that the meeting has been rescheduled to Friday.",
        "label": {"Formality": 95, "Energy": 20, "Intimacy": 5,  "Humor": 5,  "Curiosity": 10},
        "style": "formal",
    },
    {
        "utterance": "I would appreciate your prompt response at your earliest convenience.",
        "label": {"Formality": 90, "Energy": 25, "Intimacy": 10, "Humor": 5,  "Curiosity": 10},
        "style": "formal",
    },
    {
        "utterance": "Furthermore, the data suggests a significant correlation between the two variables.",
        "label": {"Formality": 95, "Energy": 15, "Intimacy": 5,  "Humor": 5,  "Curiosity": 55},
        "style": "formal",
    },
    {
        "utterance": "Pursuant to our previous discussion, I wish to confirm the arrangement.",
        "label": {"Formality": 95, "Energy": 15, "Intimacy": 10, "Humor": 5,  "Curiosity": 10},
        "style": "formal",
    },

    # ── HUMOR / MEME ─────────────────────────────────────────────────────────
    {
        "utterance": "omg have you seen that new meme?? it literally made me cry laughing 😂😂",
        "label": {"Formality": 5,  "Energy": 85, "Intimacy": 60, "Humor": 90, "Curiosity": 35},
        "style": "humor",
    },
    {
        "utterance": "LMAOOO the audacity of this person I literally cannot 💀",
        "label": {"Formality": 5,  "Energy": 90, "Intimacy": 50, "Humor": 95, "Curiosity": 20},
        "style": "humor",
    },
    {
        "utterance": "not me sending this meme to everyone I know at 3am lol",
        "label": {"Formality": 10, "Energy": 70, "Intimacy": 65, "Humor": 85, "Curiosity": 20},
        "style": "humor",
    },
    {
        "utterance": "plot twist: the real treasure was the memes we made along the way",
        "label": {"Formality": 15, "Energy": 60, "Intimacy": 55, "Humor": 90, "Curiosity": 30},
        "style": "humor",
    },
    {
        "utterance": "okay but the way this situation said 'main character energy' 💀💀",
        "label": {"Formality": 5,  "Energy": 80, "Intimacy": 55, "Humor": 95, "Curiosity": 20},
        "style": "humor",
    },

    # ── CURIOUS / INTELLECTUAL ───────────────────────────────────────────────
    {
        "utterance": "Why do you think people struggle with English conversation?",
        "label": {"Formality": 55, "Energy": 40, "Intimacy": 35, "Humor": 10, "Curiosity": 80},
        "style": "curious",
    },
    {
        "utterance": "Have you ever wondered what makes someone truly fluent in a language?",
        "label": {"Formality": 60, "Energy": 40, "Intimacy": 40, "Humor": 10, "Curiosity": 90},
        "style": "curious",
    },
    {
        "utterance": "What do you think is the best way to learn slang naturally?",
        "label": {"Formality": 45, "Energy": 45, "Intimacy": 45, "Humor": 20, "Curiosity": 85},
        "style": "curious",
    },
    {
        "utterance": "I'm really curious — how do different cultures use humor differently?",
        "label": {"Formality": 50, "Energy": 45, "Intimacy": 50, "Humor": 25, "Curiosity": 90},
        "style": "curious",
    },
    {
        "utterance": "Can you explain what makes a conversation feel natural vs scripted?",
        "label": {"Formality": 55, "Energy": 35, "Intimacy": 35, "Humor": 10, "Curiosity": 85},
        "style": "curious",
    },

    # ── MIXED / NEUTRAL ──────────────────────────────────────────────────────
    {
        "utterance": "That's a really interesting point, I hadn't thought of it that way.",
        "label": {"Formality": 55, "Energy": 40, "Intimacy": 45, "Humor": 15, "Curiosity": 60},
        "style": "neutral",
    },
    {
        "utterance": "honestly, I think I'm getting better at English but it's still hard sometimes",
        "label": {"Formality": 35, "Energy": 40, "Intimacy": 60, "Humor": 15, "Curiosity": 35},
        "style": "neutral",
    },
    {
        "utterance": "I don't know, maybe we should try something different?",
        "label": {"Formality": 40, "Energy": 35, "Intimacy": 45, "Humor": 15, "Curiosity": 55},
        "style": "neutral",
    },
    {
        "utterance": "Yeah that makes sense, I think I understand what you mean now.",
        "label": {"Formality": 40, "Energy": 35, "Intimacy": 50, "Humor": 10, "Curiosity": 30},
        "style": "neutral",
    },
    {
        "utterance": "Hmm, I'm not sure about that. Could you give me an example?",
        "label": {"Formality": 50, "Energy": 35, "Intimacy": 40, "Humor": 10, "Curiosity": 75},
        "style": "neutral",
    },
]

# 스타일별 분류
STYLES = list({d["style"] for d in DATASET})

def get_by_style(style: str) -> list:
    return [d for d in DATASET if d["style"] == style]

def get_all() -> list:
    return DATASET
