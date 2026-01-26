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
                max_tokens=5  # Minimalna odpowiedź dla szybkości
            )
            return True
        except Exception:
            # Jeśli wystąpił błąd, połączenie nie działa
            return False
