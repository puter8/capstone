# -*- coding: utf-8 -*-
"""
Rule-Based Utterance Analyzer
==============================
Analyzes English utterances and extracts 5-axis personality scores.
This is the core self-developed model of the CHARACTER MATRIX system.

Axes:
  Formality  (0=slang/casual, 100=highly formal)
  Energy     (0=low energy, 100=high energy)
  Intimacy   (0=distant, 100=very close/personal)
  Humor      (0=serious, 100=humorous/playful)
  Curiosity  (0=declarative, 100=curious/questioning)
"""
import re

# ---------------------------------------------------------------------------
# 키워드 딕셔너리 (Keyword Dictionaries)
# 각 딕셔너리는 특정 언어적 특성을 나타내는 단어/구(phrase) 목록.
# 발화에서 이 단어들이 몇 개 등장하는지 세어서 각 축 점수를 계산하는 데 사용됨.
# ---------------------------------------------------------------------------

# 슬랭/비격식 단어 목록
# → Formality(격식도)를 낮추고, Energy·Intimacy·Humor를 높이는 신호
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

# 격식체 단어/구 목록
# → Formality(격식도)를 높이고, Intimacy·Humor를 낮추는 신호
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

# 고에너지 단어 목록
# → Energy(에너지)를 높이는 신호 (감탄, 과장, 강조 표현들)
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

# 친밀도 단어 목록
# → Intimacy(친밀도)를 높이는 신호 (호칭, 안부, 개인적 감정 표현)
INTIMATE_WORDS = {
    "my friend", "bestie", "babe", "bby", "honey", "sweetheart", "darling",
    "mate", "buddy", "pal", "dude", "man", "bro", "sis", "fam",
    "i miss", "i love", "thinking of you", "how are you", "how r u",
    "you okay", "u ok", "are you good", "hope you're", "hope ur",
    "just wanted to", "honestly", "between us", "just us", "our secret",
    "tell me everything", "i need to tell you", "guess what",
    "did you know", "you won't believe",
}

# 유머/밈 단어 목록
# → Humor(유머)를 높이는 신호 (웃음 표현, 밈 문구, 유머 이모지)
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

# 호기심/탐구 단어 목록
# → Curiosity(탐구심)를 높이는 신호 (의문사, 질문 유도 표현, 설명 요청)
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
# 정규식 패턴 (Pattern Matchers)
# 키워드 딕셔너리로 잡기 어려운 언어적 특징을 정규식으로 감지함.
# ---------------------------------------------------------------------------

# 영어 축약형 패턴 (don't, i'm, you're 등)
# → 구어체(비격식) 신호. Formality↓, Intimacy↑
CONTRACTION_PATTERN = re.compile(
    r"\b(don't|doesn't|didn't|won't|can't|couldn't|wouldn't|shouldn't|"
    r"isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|i'm|i've|i'll|"
    r"i'd|you're|you've|you'll|you'd|he's|she's|it's|we're|they're|"
    r"that's|what's|where's|who's|how's|there's|here's)\b",
    re.IGNORECASE,
)
# 이모지 패턴 (😂💀🤣 등 유니코드 이모지)
# → Formality↓, Energy↑, Humor↑, Intimacy↑
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\U00002600-\U000027FF\U0000FE00-\U0000FE0F]"
)
# 느낌표 패턴 (!) → Energy↑, Formality↓
EXCLAMATION_PATTERN = re.compile(r"!")
# 물음표 패턴 (?) → Curiosity↑
QUESTION_PATTERN = re.compile(r"\?")
# 말줄임표 패턴 (...) → 현재 점수 계산에 직접 사용되지 않음 (확장 가능성 유지)
ELLIPSIS_PATTERN = re.compile(r"\.\.\.")
# 연속 대문자 단어 패턴 (LMAOOO, WHAT 등 2글자 이상)
# → Energy↑ (소리지르는 느낌, 강한 감정 표현)
CAPS_WORD_PATTERN = re.compile(r"\b[A-Z]{2,}\b")
# 반복 구두점 패턴 (!!, ??, !? 등)
# → Energy↑, Humor↑, Formality↓
REPEATED_PUNCT_PATTERN = re.compile(r"[!?]{2,}")

def _tokenize(text: str) -> list[str]:
    """
    [STEP 1] 소문자 변환 + 토크나이징

    입력 텍스트를 소문자 단어 리스트로 변환.
    정규식 [a-z']+ 로 알파벳과 아포스트로피만 추출함.
      - 숫자, !, ?, 이모지, 공백 등은 모두 제외 → 별도 패턴으로 따로 감지
      - 아포스트로피(') 포함 → don't, i'm 같은 축약형이 한 토큰으로 유지됨

    예시:
      "Yo what's up LOL!!" → ["yo", "what's", "up", "lol"]
    """
    return re.findall(r"[a-z']+", text.lower())


def _count_keyword_hits(tokens: list[str], text_lower: str, keyword_set: set) -> int:
    """
    [STEP 2] 키워드 딕셔너리 매칭

    발화에서 특정 키워드 딕셔너리의 단어/구가 몇 개 등장하는지 셈.

    단어 vs 구(phrase) 처리 방식:
      - 단어 (공백 없음): 토큰 리스트에서 정확히 일치 검색
          예: "lol" → tokens 안에 "lol"이 있는지 확인
      - 구 (공백 포함): 원문 전체에서 부분 문자열 검색
          예: "no cap" → text_lower에 "no cap"이 포함되는지 확인
          (토큰 분리하면 "no", "cap"으로 쪼개져서 구 매칭 불가)

    Returns:
      매칭된 키워드 개수 (같은 단어가 여러 번 나와도 1로 카운트)
    """
    count = 0
    for kw in keyword_set:
        if " " in kw:           # 구(phrase): 원문 전체에서 부분 문자열 검색
            if kw in text_lower:
                count += 1
        else:                   # 단어: 토큰 리스트에서 정확히 일치 검색
            if kw in tokens:
                count += 1
    return count


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

def analyze_utterance(text: str) -> dict:
    """
    영어 발화를 입력받아 5축 점수(0~100)를 반환하는 메인 분석 함수.

    전체 처리 흐름:
      STEP 1: 소문자 변환 + 토크나이징
      STEP 2: 6종 키워드 딕셔너리 매칭 → 각 키워드 히트 수 계산
      STEP 3: 6종 정규식 패턴 감지 → 이모지/!/?/대문자 단어 수 계산
      STEP 4: 문장 평균 길이 계산 (격식도 보조 지표)
      STEP 5: 각 축 점수 계산 (기준값 + 신호 가중 합산)
      STEP 6: 0~100 클리핑 후 반환

    Returns:
        dict: {Formality, Energy, Intimacy, Humor, Curiosity} 각 0~100
    """
    # STEP 1: 소문자 변환 + 토크나이징
    text_lower = text.lower()           # 소문자 변환본 (구 검색 및 패턴 매칭용)
    tokens = _tokenize(text_lower)      # 단어 토큰 리스트
    word_count = max(len(tokens), 1)    # 0 나누기 방지용 최솟값 1

    # STEP 2: 6종 키워드 딕셔너리 매칭
    slang_hits     = _count_keyword_hits(tokens, text_lower, SLANG_WORDS)      # 슬랭 단어 수
    formal_hits    = _count_keyword_hits(tokens, text_lower, FORMAL_WORDS)     # 격식 단어 수
    energy_hits    = _count_keyword_hits(tokens, text_lower, HIGH_ENERGY_WORDS)# 고에너지 단어 수
    intimate_hits  = _count_keyword_hits(tokens, text_lower, INTIMATE_WORDS)   # 친밀 단어 수
    humor_hits     = _count_keyword_hits(tokens, text_lower, HUMOR_WORDS)      # 유머 단어 수
    curiosity_hits = _count_keyword_hits(tokens, text_lower, CURIOSITY_WORDS)  # 호기심 단어 수

    # STEP 3: 정규식 패턴 감지
    contraction_count    = len(CONTRACTION_PATTERN.findall(text))   # 축약형 수 (don't, i'm 등)
    emoji_count          = len(EMOJI_PATTERN.findall(text))          # 이모지 수
    exclamation_count    = len(EXCLAMATION_PATTERN.findall(text))    # ! 개수
    question_count       = len(QUESTION_PATTERN.findall(text))       # ? 개수
    caps_word_count      = len(CAPS_WORD_PATTERN.findall(text))      # 연속 대문자 단어 수 (LMAO 등)
    repeated_punct_count = len(REPEATED_PUNCT_PATTERN.findall(text)) # 반복 구두점 수 (!!, ?? 등)

    # STEP 4: 문장 평균 길이 계산 (격식도 보조 지표)
    # 긴 문장 = 복잡한 구조 = 격식체일 가능성 높음
    sentences = re.split(r"[.!?]+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_len = word_count / max(len(sentences), 1)

    # STEP 5: 각 축 점수 계산 ──────────────────────────────────────────────

    # Formality (격식도): 기준값 40에서 시작
    #   올라가는 신호: 격식 단어(+8), 긴 문장(최대 +20)
    #   내려가는 신호: 슬랭(-6), 축약형(-4), 이모지(-10), !(-3), !!(-5)
    formality = 40
    formality += formal_hits * 8            # 격식 단어 1개당 +8
    formality -= slang_hits * 6             # 슬랭 단어 1개당 -6
    formality -= contraction_count * 4      # 축약형 1개당 -4
    formality -= emoji_count * 10           # 이모지 1개당 -10 (가장 강한 비격식 신호)
    formality -= exclamation_count * 3      # ! 1개당 -3
    formality -= repeated_punct_count * 5   # !! ?? 1개당 -5
    formality += min(max((avg_sentence_len - 10) * 1.5, -10), 20)  # 문장 길이 보정 (-10~+20)
    formality = max(0, min(100, round(formality)))  # 0~100 클리핑

    # Energy (에너지): 기준값 30에서 시작
    #   올라가는 신호: 고에너지 단어(+8), !( +7), 대문자 단어(+8), !!( +6), 이모지(+7), 슬랭(+4), 유머(+4)
    energy = 30
    energy += energy_hits * 8              # 고에너지 단어 1개당 +8
    energy += exclamation_count * 7        # ! 1개당 +7
    energy += caps_word_count * 8          # 대문자 단어 1개당 +8 (소리지르는 느낌)
    energy += repeated_punct_count * 6     # !! ?? 1개당 +6
    energy += emoji_count * 7             # 이모지 1개당 +7
    energy += slang_hits * 4              # 슬랭도 활발한 대화 신호
    energy += humor_hits * 4              # 유머 텍스트는 보통 에너지도 높음
    energy = max(0, min(100, round(energy)))

    # Intimacy (친밀도): 기준값 20에서 시작
    #   올라가는 신호: 친밀 단어(+10), 슬랭(+4), 축약형(+4), 이모지(+5)
    #   내려가는 신호: 격식 단어(-6) → 격식체일수록 거리감 있음
    intimacy = 20
    intimacy += intimate_hits * 10         # 친밀 단어 1개당 +10 (가장 강한 신호)
    intimacy += slang_hits * 4             # 슬랭 = 편한 관계 신호
    intimacy += contraction_count * 4     # 축약형 = 구어체 = 친근함
    intimacy -= formal_hits * 6           # 격식 단어 = 거리감
    intimacy += emoji_count * 5           # 이모지 = 감정 표현 = 친근함
    intimacy = max(0, min(100, round(intimacy)))

    # Humor (유머): 기준값 10에서 시작
    #   올라가는 신호: 유머 단어(+10), 이모지(+8), !!(+5), 슬랭(+3)
    #   내려가는 신호: 격식 단어(-5) → 격식체 = 진지한 분위기
    humor = 10
    humor += humor_hits * 10              # 유머 단어 1개당 +10 (가장 강한 신호)
    humor += emoji_count * 8              # 이모지 = 유머/감정 표현
    humor += repeated_punct_count * 5    # !! ?? = 과장된 반응
    humor -= formal_hits * 5             # 격식 단어가 많으면 유머 점수 하락
    humor += slang_hits * 3              # 슬랭도 유머 신호
    humor = max(0, min(100, round(humor)))

    # Curiosity (탐구심): 기준값 15에서 시작
    #   올라가는 신호: 호기심 단어(+8), ?(+12, 가장 강한 신호), 격식 단어(+3, 격식체 질문도 탐구적)
    #   내려가는 신호: !(-2) → 감탄은 질문과 반대 방향
    curiosity = 15
    curiosity += curiosity_hits * 8       # 호기심 단어 1개당 +8
    curiosity += question_count * 12     # ? 1개당 +12 (가장 강한 탐구 신호)
    curiosity += formal_hits * 3         # 격식체 질문도 탐구적 성격
    curiosity -= exclamation_count * 2   # ! 는 탐구보다 감탄/에너지 신호
    curiosity = max(0, min(100, round(curiosity)))

    return {
        "Formality": formality,
        "Energy": energy,
        "Intimacy": intimacy,
        "Humor": humor,
        "Curiosity": curiosity,
    }
