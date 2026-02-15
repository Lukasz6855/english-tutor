# -*- coding: utf-8 -*-
"""
Moduł do komunikacji z API OpenAI
Obsługuje generowanie tekstu (GPT) oraz konwersję tekstu na mowę (TTS)
"""

# Importowanie biblioteki OpenAI
from openai import OpenAI

# Importowanie konfiguracji
from config import OPENAI_MODEL, OPENAI_TTS_MODEL, DEFAULT_VOICE, SYSTEM_PROMPT


class OpenAIHelper:
    """
    Klasa pomocnicza do komunikacji z API OpenAI
    """
    
    def __init__(self, api_key: str):
        """
        Inicjalizacja klienta OpenAI
        
        Args:
            api_key: Klucz API OpenAI
        """
        # Tworzenie klienta OpenAI z podanym kluczem API
        self.client = OpenAI(api_key=api_key)
        
        # Zapisanie klucza do późniejszego użycia
        self.api_key = api_key
    
    def chat(self, user_message: str, conversation_history: list = None) -> str:
        """
        Wysyła wiadomość do modelu GPT i zwraca odpowiedź
        
        Args:
            user_message: Wiadomość od użytkownika
            conversation_history: Lista poprzednich wiadomości (opcjonalnie)
            
        Returns:
            Odpowiedź modelu jako string
        """
        # Jeśli nie podano historii, tworzymy pustą listę
        if conversation_history is None:
            conversation_history = []
        
        # Budowanie listy wiadomości dla API
        messages = [
            # Prompt systemowy definiujący zachowanie asystenta
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Dodanie historii konwersacji
        messages.extend(conversation_history)
        
        # Dodanie aktualnej wiadomości użytkownika
        messages.append({"role": "user", "content": user_message})
        
        # Wysłanie zapytania do API OpenAI
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,  # Model z konfiguracji (gpt-4o)
            messages=messages,   # Lista wiadomości
            temperature=0.7      # Kreatywność odpowiedzi (0-1)
        )
        
        # Zwrócenie tekstu odpowiedzi
        return response.choices[0].message.content
    
    def generate_words(self, prompt: str) -> str:
        """
        Generuje listę słówek na podstawie promptu
        
        Args:
            prompt: Prompt z instrukcjami generowania słówek
            
        Returns:
            Wygenerowana lista słówek jako string
        """
        # Budowanie wiadomości dla API
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        # Wysłanie zapytania do API
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7
        )
        
        # Zwrócenie wygenerowanej listy słówek
        return response.choices[0].message.content
    
    def text_to_speech(self, text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0) -> bytes:
        """
        Konwertuje tekst na mowę przy użyciu OpenAI TTS
        
        Args:
            text: Tekst do konwersji na mowę
            voice: Głos lektora (domyślnie 'echo')
            speed: Szybkość mowy (0.25 - 4.0, domyślnie 1.0)
            
        Returns:
            Dane audio w formacie MP3 jako bytes
        """
        # Wysłanie zapytania do API TTS
        response = self.client.audio.speech.create(
            model=OPENAI_TTS_MODEL,  # Model TTS z konfiguracji
            voice=voice,             # Wybrany głos
            input=text,              # Tekst do przeczytania
            speed=speed              # Szybkość mowy
        )
        
        # Zwrócenie danych audio jako bytes
        return response.content
    
    def extract_topic_name(self, user_topic: str) -> str:
        """
        Ekstraktuje krótką nazwę tematu z promptu użytkownika przy użyciu AI
        
        Args:
            user_topic: Temat słówek wpisany przez użytkownika (np. "słówka o podróżowaniu z poziomu C1/C2")
            
        Returns:
            Krótka nazwa tematu (2-4 słowa po polsku) bez przedrostka "Słówka - "
        """
        prompt = f"""Użytkownik chce wygenerować słówka na temat: "{user_topic}"

Na podstawie tego opisu, stwórz TYLKO krótką, zwięzłą nazwę pliku (2-4 słowa maksymalnie, po polsku).

Przykłady:
- Użytkownik: "słówka o podróżowaniu z poziomu C1/C2" → Nazwa: "podróżowanie C1/C2"
- Użytkownik: "jedzenie w restauracji dla początkujących" → Nazwa: "jedzenie i restauracje"
- Użytkownik: "czasowniki biznesowe" → Nazwa: "biznes"
- Użytkownik: "sport fitness advanced" → Nazwa: "sport i fitness"

NIE DODAWAJ niczego więcej - tylko nazwa tematu, bez przedrostka "Słówka - ", bez cudzysłowów, bez dodatkowych wyjaśnień.

Temat użytkownika: "{user_topic}"

Nazwa pliku:"""
        
        # Wysłanie zapytania do API
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Jesteś ekspertem w kategoryzacji tematów. Odpowiadasz TYLKO krótką nazwą tematu, bez dodatkowych słów."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Niska temperatura dla bardziej przewidywalnych wyników
            max_completion_tokens=30     # Krótka odpowiedź
        )
        
        # Zwrócenie nazwy tematu (usuwamy białe znaki i ewentualne cudzysłowy)
        topic = response.choices[0].message.content.strip().strip('"').strip("'")
        return topic
    
    def test_connection(self) -> bool:
        """
        Testuje połączenie z API OpenAI
        
        Returns:
            True jeśli połączenie działa, False w przeciwnym razie
        """
        try:
            # Próba wysłania prostego zapytania
            self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_completion_tokens=5  # Minimalna odpowiedź dla szybkości
            )
            return True
        except Exception:
            # Jeśli wystąpił błąd, połączenie nie działa
            return False
