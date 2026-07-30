# Pally 5-Axis Labeling Guide

This guide defines how to label utterances for the ML axis analyzer.

## Core Principle: Conversation First

Pally is a spoken conversation app. Label only utterances that a learner might realistically say out loud during a conversation with Pally.

Do not use essay, legal, academic, corporate email, or report-style sentences as normal training examples. If a user can read it in a paper but would not naturally say it in a voice chat, it does not belong in the core dataset.

## Output Format

Each row must use the same 5-axis contract as `/api/chat`.

```json
{
  "utterance": "could you say that again a little slower?",
  "axes": {
    "Formality": 55,
    "Energy": 30,
    "Intimacy": 35,
    "Humor": 5,
    "Curiosity": 75
  },
  "style": "learner_request",
  "split": "train",
  "notes": "natural spoken clarification request"
}
```

## Axis Rules

| Axis | Low Score | High Score |
|---|---|---|
| Formality | slang, contractions, very casual greeting | polite, careful, respectful spoken English |
| Energy | calm, short, flat | excited, emphatic, emotional, high arousal |
| Intimacy | distant, task-only | friendly, personal, supportive, direct address |
| Humor | literal, serious | jokes, exaggeration, memes, playful framing |
| Curiosity | declarative, closed statement | questions, wonder, requests for explanation |

## Formality Clarification

High Formality does not mean academic or business writing. For Pally, high Formality means the user is speaking politely and carefully in a conversation.

Good high-formality examples:

- "Could you please explain that one more time?"
- "I would like to practice ordering politely at a cafe."
- "May I ask how to say this more naturally?"

Avoid as core training examples:

- "I would like to formally inquire about the implications of this matter."
- "Furthermore, the data suggests a significant correlation."
- "Please be advised that the meeting has been rescheduled."

## Labeling Scale

- `0-20`: very low signal
- `21-40`: low to mild signal
- `41-60`: moderate signal
- `61-80`: strong signal
- `81-100`: dominant signal

## Rules

- Keep every axis in the `0-100` range.
- Label the utterance as spoken English, not formal writing.
- Learner mistakes, short fragments, self-corrections, and natural pauses are valid if they sound like conversation.
- Use polite spoken examples for high Formality, not essay/legal/business vocabulary.
- Reddit vocabulary is only useful when it is plausibly spoken in conversation or needed for conversation comprehension.
- Do not use Reddit source text as ML training data unless Reddit explicitly allows that use.
- If two axes conflict, label both. Example: a polite question can be high Formality and high Curiosity.
- Preserve the original utterance exactly; put interpretation in `notes`.

## Week 2 Dataset Target

- Use conversation-centered hand-labeled examples as the Week 2 seed data.
- Add learner-style examples before adding synthetic edge cases.
- Target 150-300 labeled utterances by the end of the data-building phase.
- Evaluation should prioritize actual voice conversation cases: greetings, clarification, roleplay, opinions, small talk, corrections, feedback reactions, and casual slang used in speech.