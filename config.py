# -*- coding: utf-8 -*-
"""
Plik konfiguracyjny aplikacji - zawiera stałe i ustawienia
"""

# ============================================================
# KONFIGURACJA OPENAI
# ============================================================

# Model OpenAI do generowania słówek (najnowszy dostępny - styczeń 2026)
OPENAI_MODEL = "gpt-5.2"

# Model do konwersji tekstu na mowę
OPENAI_TTS_MODEL = "tts-1"

# Domyślny głos lektora (echo - męski głos)
DEFAULT_VOICE = "echo"

# Dostępne głosy OpenAI TTS
AVAILABLE_VOICES = {
    "alloy": "Alloy (neutralny)",
    "echo": "Echo (męski)",
    "fable": "Fable (brytyjski akcent)",
    "onyx": "Onyx (głęboki męski)",
    "nova": "Nova (żeński)",
    "shimmer": "Shimmer (ciepły żeński)"
}

# ============================================================
# KONFIGURACJA AUDIO
# ============================================================

# Domyślne ustawienia generowania audio
DEFAULT_AUDIO_SETTINGS = {
    "speed": 1.0,           # Szybkość mowy (0.5 - 2.0)
    "pause_between": 2.0,   # Przerwa między hasłami (sekundy)
    "repetitions": 1,       # Ile razy powtórzyć hasło (1 lub 2)
    "include_examples": True,  # Czy czytać przykładowe zdania
    "test_mode": None       # None / "pl_to_en" / "en_to_pl"
}

# Przerwa w trybie testowym (sekundy) - czas na odpowiedź użytkownika
TEST_PAUSE_DURATION = 2.0

# ============================================================
# KONFIGURACJA KATEGORII SŁÓWEK
# ============================================================

# Dostępne kategorie słówek (jak w przykładzie)
WORD_CATEGORIES = [
    "CZASOWNIKI",
    "PRZYMIOTNIKI", 
    "PHRASAL VERBS",
    "RZECZOWNIKI",
    "PRZYSŁÓWKI",
    "WYRAŻENIA IDIOMATYCZNE",
    "INNE"
]

# ============================================================
# PROMPT SYSTEMOWY DLA AI
# ============================================================

# Prompt systemowy definiujący zachowanie asystenta
SYSTEM_PROMPT = """Jesteś ekspertem od nauki języka angielskiego. Pomagasz użytkownikowi w nauce słówek angielskich.

Twoje zadania:
1. Generowanie list słówek na podstawie tematyki podanej przez użytkownika
2. Proponowanie własnych list słówek, gdy użytkownik o to poprosi
3. Dostosowywanie poziomu trudności do potrzeb użytkownika

WAŻNE ZASADY FORMATOWANIA:
- Każde słówko musi zawierać: słowo angielskie, wymowę fonetyczną w nawiasie, polskie tłumaczenie
- Po każdym słówku dodaj przykładowe zdanie z "ex:"
- Grupuj słówka według kategorii (CZASOWNIKI, PRZYMIOTNIKI, PHRASAL VERBS, itp.)

PRZYKŁADOWY FORMAT:
CZASOWNIKI

1. accomplish (akomplisz) – osiągnąć, dokonać
ex: She accomplished her goal of running a marathon.

2. achieve (acziww) – osiągnąć
ex: He achieved great success in his career.

PRZYMIOTNIKI

3. ambitious (ambiszys) – ambitny
ex: She is very ambitious and hardworking.

Zawsze odpowiadaj po polsku, ale słówka i przykłady podawaj po angielsku z polskim tłumaczeniem."""

# ============================================================
# PROMPT DO GENEROWANIA SŁÓWEK
# ============================================================

GENERATION_PROMPT_TEMPLATE = """Wygeneruj listę {count} słówek angielskich na temat: {topic}

WAŻNE:
1. NIE POWTARZAJ tych słówek, które już były wygenerowane wcześniej:
{existing_words}

2. Użyj dokładnie tego formatu dla każdego słówka:
[numer]. [słówko angielskie] ([wymowa fonetyczna]) – [polskie tłumaczenie]
ex: [przykładowe zdanie po angielsku]

3. Pogrupuj słówka według kategorii (np. CZASOWNIKI, PRZYMIOTNIKI, PHRASAL VERBS, RZECZOWNIKI)
4. Każda kategoria powinna być oddzielona linią: ---------------------

Przykład poprawnego formatu:
CZASOWNIKI

1. accomplish (akomplisz) – osiągnąć, dokonać
ex: She accomplished her goal of running a marathon.

2. achieve (acziww) – osiągnąć
ex: He achieved great success in his career.

-------------------------------------------------------------------------------------
PRZYMIOTNIKI

3. ambitious (ambiszys) – ambitny
ex: She is very ambitious and hardworking.

Wygeneruj teraz {count} nowych, unikalnych słówek:"""
