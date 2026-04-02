# -*- coding: utf-8 -*-
"""
Rule-Based Utterance Analyzer
==============================
Analyzes English utterances and extracts 5-axis personality scores.
This is the core self-developed model of the Emotion MATRIX system.

Axes:
  Formality  (0=slang/casual, 100=highly formal)
  Energy     (0=low energy, 100=high energy)
  Intimacy   (0=distant, 100=very close/personal)
  Humor      (0=serious, 100=humorous/playful)
  Curiosity  (0=declarative, 100=curious/questioning)
"""
import re

# ---------------------------------------------------------------------------
# Keyword dictionaries
# ---------------------------------------------------------------------------

SLANG_WORDS = {
    "yo", "lol", "lmao", "lmfao", "omg", "omfg", "wtf", "bruh", "bro",
    "sis", "fam", "ngl", "tbh", "imo", "idk", "idc", "smh", "fr",
    "nah", "yep", "yup", "gonna", "wanna", "gotta", "kinda", "sorta",
    "tryna", "dunno", "legit", "lowkey", "highkey", "vibe", "slay",
    "bet", "sus", "cap", "no cap", "bussin", "goated", "rizz", "mid",
    "chefs kiss", "hits different", "understood the assignment", "rent free",
    "main character", "era", "it's giving", "ate", "periodt", "ick",
    "touch grass", "understood", "sheesh", "based", "cringe", "chad",
    "simp", "noob", "rekt", "gg", "af", "nvm", "rn", "asap", "fyi",
    "iirc", "btw", "tbf", "istg", "irl", "dm", "hmu",
    "what's up", "wassup", "sup", "whatup", "u", "ur", "r u", "cya",
    "g2g", "ttyl", "brb", "bc", "cuz", "cause",
    "dude", "literally", "obsessed", "totally", "bestie",
    "so good", "so bad", "no way", "for real", "deadass",
}

FORMAL_WORDS = {
    "therefore", "furthermore", "moreover", "nevertheless", "consequently",
    "accordingly", "henceforth", "herein", "herewith", "thereof",
    "notwithstanding", "pursuant", "whereas", "hereby", "aforementioned",
    "subsequently", "respectively", "predominantly", "approximately",
    "commence", "endeavor", "facilitate", "utilize", "ascertain",
    "inquire", "request", "inform", "notify", "acknowledge", "confirm",
    "proceed", "kindly", "sincerely", "regards", "dear", "please",
    "would like", "i would", "could you", "may i", "shall", "ought",
    "formally", "officially", "professionally", "respectfully",
    "implications", "pertaining", "regarding", "concerning",
    "in accordance", "as per", "with respect to", "in regards to",
    "at your earliest convenience", "i would be happy",
    "please be advised", "please note",
    # additional formal / academic vocab
    "methodology", "proposed", "arrangement", "discussion", "elaborate",
    "report", "writing to", "end of business", "am writing", "i am writing",
    "previous discussion", "socioeconomic", "policy", "analysis",
    "appreciate your", "look forward", "continued collaboration",
    "be happy to", "provide a", "thorough", "explanation",
    "thank you for", "your inquiry",
}

HIGH_ENERGY_WORDS = {
    "amazing", "awesome", "incredible", "fantastic", "brilliant", "epic",
    "insane", "wild", "crazy", "literally", "absolutely", "totally",
    "definitely", "obsessed", "love", "adore", "excited", "thrilled",
    "pumped", "hyped", "can't wait", "so good", "so bad", "so weird",
    "dying", "dead", "cannot", "i can't", "i can not", "burst",
    "screaming", "crying", "living for", "here for", "all for",
    "let's go", "lets go", "yesss", "noooo", "omg yes", "omg no",
    "wait what", "no way", "shut up", "stop it", "get out",
}

INTIMATE_WORDS = {
    "my friend", "bestie", "babe", "bby", "honey", "sweetheart", "darling",
    "mate", "buddy", "pal", "dude", "man", "bro", "sis", "fam",
    "i miss", "i love", "thinking of you", "how are you", "how r u",
    "you okay", "u ok", "are you good", "hope you're", "hope ur",
    "just wanted to", "honestly", "between us", "just us", "our secret",
    "tell me everything", "i need to tell you", "guess what",
    "did you know", "you won't believe",
}

HUMOR_WORDS = {
    "lol", "lmao", "lmfao", "haha", "hehe", "hihi", "xd", "xD",
    "💀", "😂", "🤣", "😭", "💀", "👀", "🙃", "😅",
    "dead", "dying", "i'm crying", "i can't", "i literally cannot",
    "periodt", "no but seriously", "not gonna lie but", "plot twist",
    "caught in 4k", "rent free", "understood the assignment",
    "hits different", "main character", "not me", "the way",
    "bestie what", "okay but", "though", "tho", "ngl",
    "imagine", "could you imagine", "the audacity",
    "meme", "memes", "tweet", "twitter", "reddit", "tiktok",
    "lowkey laughing", "crying laughing", "cry laughing", "made me laugh",
    # high-frequency humor signals
    "omg", "literally", "peak", "ate", "no crumbs", "ate and left",
    "i'm so normal", "so normal", "ironic", "sarcastic",
    "crying at", "cry at", "crying over",
}

CURIOSITY_WORDS = {
    "why", "how", "what", "when", "where", "who", "which", "whose",
    "wonder", "curious", "interesting", "fascinating", "really",
    "tell me", "explain", "elaborate", "clarify", "describe",
    "what do you think", "your opinion", "what's your", "do you think",
    "have you ever", "have you seen", "did you know", "ever wonder",
    "what if", "imagine if", "suppose", "hypothetically",
    "can you", "could you", "would you", "will you", "should i",
    "is it", "are there", "does it", "do you",
}

# ---------------------------------------------------------------------------
# Pattern matchers
# ---------------------------------------------------------------------------

CONTRACTION_PATTERN = re.compile(
    r"\b(don't|doesn't|didn't|won't|can't|couldn't|wouldn't|shouldn't|"
    r"isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|i'm|i've|i'll|"
    r"i'd|you're|you've|you'll|you'd|he's|she's|it's|we're|they're|"
    r"that's|what's|where's|who's|how's|there's|here's)\b",
    re.IGNORECASE,
)
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027FF\U0000FE00-\U0000FE0F]"
)
EXCLAMATION_PATTERN = re.compile(r"!")
QUESTION_PATTERN = re.compile(r"\?")
ELLIPSIS_PATTERN = re.compile(r"\.\.\.")
CAPS_WORD_PATTERN = re.compile(r"\b[A-Z]{2,}\b")
REPEATED_PUNCT_PATTERN = re.compile(r"[!?]{2,}")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenizer."""
    return re.findall(r"[a-z']+", text.lower())


def _count_keyword_hits(tokens: list[str], text_lower: str, keyword_set: set) -> int:
    """Count how many keywords/phrases from the set appear in the text."""
    count = 0
    for kw in keyword_set:
        if " " in kw:
            if kw in text_lower:
                count += 1
        else:
            if kw in tokens:
                count += 1
    return count


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

def analyze_utterance(text: str) -> dict:
    """
    Analyze an English utterance and return 5-axis personality scores (0–100).

    Returns:
        dict with keys: Formality, Energy, Intimacy, Humor, Curiosity
    """
    text_lower = text.lower()
    tokens = _tokenize(text_lower)
    word_count = max(len(tokens), 1)

    # --- Feature extraction ---
    slang_hits = _count_keyword_hits(tokens, text_lower, SLANG_WORDS)
    formal_hits = _count_keyword_hits(tokens, text_lower, FORMAL_WORDS)
    energy_hits = _count_keyword_hits(tokens, text_lower, HIGH_ENERGY_WORDS)
    intimate_hits = _count_keyword_hits(tokens, text_lower, INTIMATE_WORDS)
    humor_hits = _count_keyword_hits(tokens, text_lower, HUMOR_WORDS)
    curiosity_hits = _count_keyword_hits(tokens, text_lower, CURIOSITY_WORDS)

    contraction_count = len(CONTRACTION_PATTERN.findall(text))
    emoji_count = len(EMOJI_PATTERN.findall(text))
    exclamation_count = len(EXCLAMATION_PATTERN.findall(text))
    question_count = len(QUESTION_PATTERN.findall(text))
    caps_word_count = len(CAPS_WORD_PATTERN.findall(text))
    repeated_punct_count = len(REPEATED_PUNCT_PATTERN.findall(text))

    # Average sentence length (proxy for complexity)
    sentences = re.split(r"[.!?]+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_len = word_count / max(len(sentences), 1)

    # --- Axis: Formality (0=casual, 100=formal) ---
    formality = 40
    formality += formal_hits * 8
    formality -= slang_hits * 6
    formality -= contraction_count * 4
    formality -= emoji_count * 10
    formality -= exclamation_count * 3
    formality -= repeated_punct_count * 5
    formality += min(max((avg_sentence_len - 10) * 1.5, -10), 20)
    formality = max(0, min(100, round(formality)))

    # --- Axis: Energy (0=low, 100=high) ---
    energy = 30
    energy += energy_hits * 8
    energy += exclamation_count * 7
    energy += caps_word_count * 8
    energy += repeated_punct_count * 6
    energy += emoji_count * 7
    energy += slang_hits * 4
    energy += humor_hits * 4   # humor-heavy text tends to be high energy
    energy = max(0, min(100, round(energy)))

    # --- Axis: Intimacy (0=distant, 100=close) ---
    intimacy = 20
    intimacy += intimate_hits * 10
    intimacy += slang_hits * 4
    intimacy += contraction_count * 4
    intimacy -= formal_hits * 6
    intimacy += emoji_count * 5
    intimacy = max(0, min(100, round(intimacy)))

    # --- Axis: Humor (0=serious, 100=funny) ---
    humor = 10
    humor += humor_hits * 10
    humor += emoji_count * 8
    humor += repeated_punct_count * 5
    humor -= formal_hits * 5
    humor += slang_hits * 3
    humor = max(0, min(100, round(humor)))

    # --- Axis: Curiosity (0=declarative, 100=curious) ---
    curiosity = 15
    curiosity += curiosity_hits * 8
    curiosity += question_count * 12
    curiosity += formal_hits * 3   # formal text often contains formal questions
    curiosity -= exclamation_count * 2
    curiosity = max(0, min(100, round(curiosity)))

    return {
        "Formality": formality,
        "Energy": energy,
        "Intimacy": intimacy,
        "Humor": humor,
        "Curiosity": curiosity,
    }
