# -*- coding: utf-8 -*-
"""
Moduł do komunikacji z bazą danych Vercel Blob
Przechowuje pliki Word oraz historię wygenerowanych słówek
"""

# Importowanie bibliotek do komunikacji HTTP
import requests
import json

# Importowanie bibliotek do operacji na plikach
from io import BytesIO
from datetime import datetime


class DatabaseManager:
    """
    Klasa do zarządzania bazą danych Vercel Blob
    Przechowuje pliki Word i historię słówek
    """
    
    # URL bazowy API Vercel Blob
    BLOB_API_URL = "https://blob.vercel-storage.com"
    
    def __init__(self, token: str):
        """
        Inicjalizacja managera bazy danych
        
        Args:
            token: Token Vercel Blob (Read/Write)
        """
        # Zapisanie tokenu do autoryzacji
        self.token = token
        
        # Nagłówki dla żądań HTTP
        self.headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # Nazwa pliku z historią słówek
        self.history_filename = "words_history.json"
    
    def upload_file(self, file_data: BytesIO, filename: str) -> dict:
        """
        Wysyła plik do Vercel Blob
        
        Args:
            file_data: Dane pliku jako BytesIO
            filename: Nazwa pliku do zapisania
            
        Returns:
            Słownik z informacjami o zapisanym pliku (url, pathname)
        """
        # URL do uploadu pliku
        url = f"{self.BLOB_API_URL}/{filename}"
        
        # Nagłówki specyficzne dla uploadu
        headers = {
            **self.headers,
            "x-api-version": "7",
            "Content-Type": "application/octet-stream"
        }
        
        # Przewinięcie bufora na początek
        file_data.seek(0)
        
        # Wysłanie żądania PUT z danymi pliku
        response = requests.put(url, headers=headers, data=file_data.read())
        
        # Sprawdzenie czy żądanie się powiodło
        response.raise_for_status()
        
        # Zwrócenie informacji o zapisanym pliku
        return response.json()
    
    def download_file(self, url: str) -> BytesIO:
        """
        Pobiera plik z Vercel Blob
        
        Args:
            url: URL pliku do pobrania
            
        Returns:
            Dane pliku jako BytesIO
        """
        # Wysłanie żądania GET
        response = requests.get(url, headers=self.headers)
        
        # Sprawdzenie czy żądanie się powiodło
        response.raise_for_status()
        
        # Zwrócenie danych jako BytesIO
        return BytesIO(response.content)
    
    def list_files(self) -> list:
        """
        Pobiera listę wszystkich plików w Vercel Blob
        
        Returns:
            Lista słowników z informacjami o plikach
        """
        # URL do listowania plików
        url = f"{self.BLOB_API_URL}?limit=1000"
        
        # Nagłówki dla listowania
        headers = {
            **self.headers,
            "x-api-version": "7"
        }
        
        # Wysłanie żądania GET
        response = requests.get(url, headers=headers)
        
        # Sprawdzenie czy żądanie się powiodło
        response.raise_for_status()
        
        # Parsowanie odpowiedzi JSON
        data = response.json()
        
        # Zwrócenie listy plików (blobs)
        return data.get('blobs', [])
    
    def delete_file(self, url: str) -> bool:
        """
        Usuwa plik z Vercel Blob
        
        Args:
            url: URL pliku do usunięcia
            
        Returns:
            True jeśli usunięcie się powiodło
        """
        # URL do usuwania plików
        delete_url = f"{self.BLOB_API_URL}/delete"
        
        # Nagłówki dla usuwania
        headers = {
            **self.headers,
            "x-api-version": "7",
            "Content-Type": "application/json"
        }
        
        # Dane żądania (lista URLi do usunięcia)
        data = {"urls": [url]}
        
        # Wysłanie żądania POST
        response = requests.post(delete_url, headers=headers, json=data)
        
        # Sprawdzenie czy żądanie się powiodło
        return response.status_code == 200
    
    def get_words_history(self) -> list:
        """
        Pobiera historię wszystkich wygenerowanych słówek
        
        Returns:
            Lista słówek (stringów) które już były wygenerowane
        """
        try:
            # Pobieranie listy plików
            files = self.list_files()
            
            # Szukanie pliku z historią
            history_file = None
            for f in files:
                if f.get('pathname', '').endswith(self.history_filename):
                    history_file = f
                    break
            
            # Jeśli nie znaleziono pliku historii, zwracamy pustą listę
            if not history_file:
                return []
            
            # Pobieranie zawartości pliku historii
            file_data = self.download_file(history_file['url'])
            
            # Parsowanie JSON
            history = json.loads(file_data.read().decode('utf-8'))
            
            return history.get('words', [])
            
        except Exception as e:
            # W przypadku błędu zwracamy pustą listę
            print(f"Błąd pobierania historii: {e}")
            return []
    
    def add_words_to_history(self, new_words: list) -> bool:
        """
        Dodaje nowe słówka do historii
        
        Args:
            new_words: Lista nowych słówek do dodania
            
        Returns:
            True jeśli zapisanie się powiodło
        """
        try:
            # Pobieranie aktualnej historii
            current_words = self.get_words_history()
            
            # Dodawanie nowych słówek (unikalne, małe litery)
            for word in new_words:
                word_lower = word.lower().strip()
                if word_lower and word_lower not in current_words:
                    current_words.append(word_lower)
            
            # Tworzenie struktury JSON
            history_data = {
                'words': current_words,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(current_words)
            }
            
            # Konwersja do JSON i BytesIO
            json_str = json.dumps(history_data, ensure_ascii=False, indent=2)
            file_data = BytesIO(json_str.encode('utf-8'))
            
            # Upload pliku historii
            self.upload_file(file_data, self.history_filename)
            
            return True
            
        except Exception as e:
            print(f"Błąd zapisywania historii: {e}")
            return False
    
    def save_word_document(self, doc_data: BytesIO, topic: str) -> dict:
        """
        Zapisuje dokument Word z listą słówek
        
        Args:
            doc_data: Dane dokumentu jako BytesIO
            topic: Temat słówek (do nazwy pliku)
            
        Returns:
            Słownik z informacjami o zapisanym pliku
        """
        # Generowanie nazwy pliku według schematu: Słówka rr.mm.dd
        date_str = datetime.now().strftime("%y.%m.%d")
        
        # Tworzenie nazwy pliku
        filename = f"Słówka {date_str}.docx"
        
        # Upload pliku
        return self.upload_file(doc_data, filename)
    
    def test_connection(self) -> bool:
        """
        Testuje połączenie z Vercel Blob
        
        Returns:
            True jeśli połączenie działa
        """
        try:
            # Próba pobrania listy plików
            self.list_files()
            return True
        except Exception:
            return False
