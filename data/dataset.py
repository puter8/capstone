# -*- coding: utf-8 -*-
"""Conversation-first seed dataset for Pally 5-axis analysis.

The examples here are spoken utterances a learner might say to Pally.
Do not add academic, legal, report, or corporate email-style sentences
as core labels for the conversation analyzer.
"""

DATASET = [
    {
        "utterance": "hey, how\u0027s your day going?",
        "label": {"Formality": 25, "Energy": 45, "Intimacy": 65, "Humor": 5, "Curiosity": 65},
        "style": "small_talk",
    },
    {
        "utterance": "could you say that again a little slower?",
        "label": {"Formality": 55, "Energy": 30, "Intimacy": 35, "Humor": 5, "Curiosity": 75},
        "style": "learner_request",
    },
    {
        "utterance": "sorry, I didn\u0027t catch the last word",
        "label": {"Formality": 50, "Energy": 25, "Intimacy": 35, "Humor": 5, "Curiosity": 45},
        "style": "learner_request",
    },
    {
        "utterance": "can we practice ordering coffee like I\u0027m at a cafe?",
        "label": {"Formality": 45, "Energy": 40, "Intimacy": 40, "Humor": 10, "Curiosity": 75},
        "style": "roleplay_request",
    },
    {
        "utterance": "I would like a small iced latte, please",
        "label": {"Formality": 70, "Energy": 25, "Intimacy": 20, "Humor": 5, "Curiosity": 5},
        "style": "formal",
    },
    {
        "utterance": "uh, can I say \u0027I have hungry\u0027 or is that wrong?",
        "label": {"Formality": 35, "Energy": 35, "Intimacy": 40, "Humor": 5, "Curiosity": 85},
        "style": "learner_question",
    },
    {
        "utterance": "wait, that\u0027s actually hilarious",
        "label": {"Formality": 15, "Energy": 65, "Intimacy": 45, "Humor": 80, "Curiosity": 10},
        "style": "humor",
    },
    {
        "utterance": "no cap, that pronunciation is so hard for me",
        "label": {"Formality": 10, "Energy": 55, "Intimacy": 55, "Humor": 25, "Curiosity": 20},
        "style": "casual",
    },
    {
        "utterance": "could you give me a more natural way to say that?",
        "label": {"Formality": 55, "Energy": 30, "Intimacy": 35, "Humor": 5, "Curiosity": 85},
        "style": "learner_request",
    },
    {
        "utterance": "I think I sound too stiff when I speak English",
        "label": {"Formality": 35, "Energy": 30, "Intimacy": 60, "Humor": 5, "Curiosity": 35},
        "style": "self_reflection",
    },
    {
        "utterance": "what does lowkey mean in this sentence?",
        "label": {"Formality": 25, "Energy": 35, "Intimacy": 30, "Humor": 10, "Curiosity": 90},
        "style": "slang_question",
    },
    {
        "utterance": "that\u0027s kind of embarrassing, but I want to try again",
        "label": {"Formality": 35, "Energy": 40, "Intimacy": 70, "Humor": 15, "Curiosity": 30},
        "style": "self_reflection",
    },
    {
        "utterance": "oh really? why do people say it like that?",
        "label": {"Formality": 30, "Energy": 45, "Intimacy": 45, "Humor": 5, "Curiosity": 90},
        "style": "curious",
    },
    {
        "utterance": "please correct me if my sentence sounds awkward",
        "label": {"Formality": 65, "Energy": 25, "Intimacy": 35, "Humor": 5, "Curiosity": 60},
        "style": "formal",
    },
    {
        "utterance": "I\u0027m nervous, but let\u0027s do a job interview practice",
        "label": {"Formality": 50, "Energy": 45, "Intimacy": 55, "Humor": 5, "Curiosity": 35},
        "style": "roleplay_request",
    },
    {
        "utterance": "hi, nice to meet you, I\u0027m Minju",
        "label": {"Formality": 45, "Energy": 35, "Intimacy": 55, "Humor": 5, "Curiosity": 5},
        "style": "greeting",
    },
    {
        "utterance": "what should I say when I meet my friend\u0027s parents?",
        "label": {"Formality": 45, "Energy": 35, "Intimacy": 50, "Humor": 5, "Curiosity": 85},
        "style": "social_question",
    },
    {
        "utterance": "that\u0027s wild, I didn\u0027t know people actually say that",
        "label": {"Formality": 15, "Energy": 65, "Intimacy": 45, "Humor": 35, "Curiosity": 55},
        "style": "casual_reaction",
    },
    {
        "utterance": "could we make this sentence sound warmer?",
        "label": {"Formality": 55, "Energy": 25, "Intimacy": 55, "Humor": 5, "Curiosity": 75},
        "style": "learner_request",
    },
    {
        "utterance": "I totally forgot the word, give me a second",
        "label": {"Formality": 25, "Energy": 40, "Intimacy": 55, "Humor": 10, "Curiosity": 10},
        "style": "repair",
    },
    {
        "utterance": "haha, I said it backwards again",
        "label": {"Formality": 15, "Energy": 55, "Intimacy": 60, "Humor": 65, "Curiosity": 10},
        "style": "humor",
    },
    {
        "utterance": "may I ask one more question about the expression?",
        "label": {"Formality": 70, "Energy": 25, "Intimacy": 30, "Humor": 5, "Curiosity": 85},
        "style": "formal",
    },
    {
        "utterance": "that sounds too serious for texting a friend, right?",
        "label": {"Formality": 35, "Energy": 35, "Intimacy": 55, "Humor": 10, "Curiosity": 80},
        "style": "register_question",
    },
    {
        "utterance": "okay, let me try the sentence one more time",
        "label": {"Formality": 35, "Energy": 40, "Intimacy": 40, "Humor": 5, "Curiosity": 20},
        "style": "practice",
    },
    {
        "utterance": "I want to sound friendly, not too formal",
        "label": {"Formality": 40, "Energy": 30, "Intimacy": 60, "Humor": 5, "Curiosity": 35},
        "style": "style_goal",
    },
    {
        "utterance": "is it rude if I say it this way?",
        "label": {"Formality": 45, "Energy": 35, "Intimacy": 35, "Humor": 5, "Curiosity": 90},
        "style": "social_question",
    },
    {
        "utterance": "bro, I keep mixing up past tense",
        "label": {"Formality": 10, "Energy": 50, "Intimacy": 60, "Humor": 20, "Curiosity": 20},
        "style": "casual",
    },
    {
        "utterance": "could you answer like a close friend this time?",
        "label": {"Formality": 45, "Energy": 30, "Intimacy": 75, "Humor": 5, "Curiosity": 60},
        "style": "conversation_control",
    },
    {
        "utterance": "oh, that makes sense now, thanks",
        "label": {"Formality": 35, "Energy": 35, "Intimacy": 55, "Humor": 5, "Curiosity": 10},
        "style": "feedback_reaction",
    },
    {
        "utterance": "what\u0027s a casual way to invite someone to lunch?",
        "label": {"Formality": 35, "Energy": 35, "Intimacy": 45, "Humor": 5, "Curiosity": 90},
        "style": "social_question",
    },
]

STYLES = sorted({item["style"] for item in DATASET})

def get_by_style(style: str) -> list:
    return [item for item in DATASET if item["style"] == style]

def get_all() -> list:
    return DATASET
