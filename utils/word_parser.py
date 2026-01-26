# -*- coding: utf-8 -*-
"""
Moduł do parsowania plików Word ze słówkami
Odczytuje dokumenty Word i wyciąga z nich listę słówek
"""

# Importowanie biblioteki do odczytu plików Word
from docx import Document

# Importowanie wyrażeń regularnych
import re

# Importowanie biblioteki do operacji na plikach
from io import BytesIO


class WordParser:
    """
    Klasa do parsowania plików Word ze słówkami
    """
    
    def __init__(self):
        """
        Inicjalizacja parsera dokumentów Word
        """
        # Brak dodatkowej konfiguracji potrzebnej przy inicjalizacji
        pass
    
    def parse_document(self, file_data: BytesIO) -> list:
        """
        Parsuje dokument Word i wyciąga listę słówek
        
        Args:
            file_data: Dane dokumentu jako BytesIO
            
        Returns:
            Lista słowników z informacjami o słówkach
        """
        # Przewinięcie bufora na początek
        file_data.seek(0)
        
        # Wczytanie dokumentu Word
        doc = Document(file_data)
        
        # Lista na sparsowane słówka
        words = []
        
        # Aktualna kategoria
        current_category = None
        
        # Aktualne słówko (do którego dodajemy przykład)
        current_word = None
        
        # Wzorzec do wyciągania słówek
        # Format: numer. słówko (wymowa) – tłumaczenie
        word_pattern = r'(\d+)\.\s+(.+?)\s*\(([^)]+)\)\s*[–-]\s*(.+)'
        
        # Wzorzec do wyciągania przykładów
        example_pattern = r'^ex:\s*(.+)$'
        
        # Przetwarzanie każdego paragrafu
        for para in doc.paragraphs:
            # Pobieranie tekstu paragrafu
            text = para.text.strip()
            
            # Pomijanie pustych paragrafów i separatorów
            if not text or re.match(r'^-+$', text):
                continue
            
            # Sprawdzanie czy to kategoria (same wielkie litery)
            if text.isupper() and len(text) > 2:
                current_category = text
                continue
            
            # Sprawdzanie czy słówko i przykład są w tej samej linii (oddzielone \n)
            # Format: "1. word (wymowa) – tłumaczenie\nex: przykład"
            if '\n' in text:
                lines_in_para = text.split('\n')
                # Pierwsza linia to słówko
                word_line = lines_in_para[0].strip()
                # Druga linia to przykład
                example_line = lines_in_para[1].strip() if len(lines_in_para) > 1 else ''
                
                # Próba dopasowania wzorca słówka
                word_match = re.match(word_pattern, word_line)
                if word_match:
                    # Jeśli było poprzednie słówko, dodaj je do listy
                    if current_word:
                        words.append(current_word)
                    
                    # Wyciągnięcie przykładu z drugiej linii
                    example_text = None
                    if example_line.lower().startswith('ex:'):
                        example_text = example_line[3:].strip()
                    
                    # Tworzenie nowego słówka
                    current_word = {
                        'number': int(word_match.group(1)),
                        'english': word_match.group(2).strip(),
                        'pronunciation': word_match.group(3).strip(),
                        'polish': word_match.group(4).strip(),
                        'example': example_text,
                        'category': current_category
                    }
                    continue
            
            # Próba dopasowania wzorca słówka (bez przykładu w tej samej linii)
            word_match = re.match(word_pattern, text)
            if word_match:
                # Jeśli było poprzednie słówko, dodaj je do listy
                if current_word:
                    words.append(current_word)
                
                # Tworzenie nowego słówka
                current_word = {
                    'number': int(word_match.group(1)),
                    'english': word_match.group(2).strip(),
                    'pronunciation': word_match.group(3).strip(),
                    'polish': word_match.group(4).strip(),
                    'example': None,
                    'category': current_category
                }
                continue
            
            # Próba dopasowania przykładu (case-insensitive)
            example_match = re.match(example_pattern, text, re.IGNORECASE)
            if example_match and current_word:
                current_word['example'] = example_match.group(1).strip()
                continue
            
            # Jeśli linia zaczyna się od "ex:" (bez względu na wielkość liter)
            if text.lower().startswith('ex:') and current_word:
                example_text = text[3:].strip()
                if example_text:
                    current_word['example'] = example_text
        
        # Dodanie ostatniego słówka
        if current_word:
            words.append(current_word)
        
        return words
    
    def parse_text(self, text: str) -> list:
        """
        Parsuje tekst i wyciąga listę słówek
        
        Args:
            text: Tekst z listą słówek
            
        Returns:
            Lista słowników z informacjami o słówkach
        """
        # Lista na sparsowane słówka
        words = []
        
        # Aktualna kategoria
        current_category = None
        
        # Aktualne słówko
        current_word = None
        
        # Wzorzec do wyciągania słówek
        # Format: numer. słówko (wymowa) – tłumaczenie
        # Używamy [^–-]+ zamiast .+ żeby nie wyciągać za dużo
        word_pattern = r'(\d+)\.\s+(.+?)\s*\(([^)]+)\)\s*[–-]\s*(.+)'
        
        # Wzorzec do wyciągania przykładów
        example_pattern = r'^ex:\s*(.+)$'
        
        # Przetwarzanie tekstu linia po linii
        lines = text.strip().split('\n')
        
        for line in lines:
            # Usuwanie białych znaków
            line = line.strip()
            
            # Pomijanie pustych linii i separatorów
            if not line or re.match(r'^-+$', line):
                continue
            
            # Sprawdzanie czy to kategoria
            if line.isupper() and len(line) > 2:
                current_category = line
                continue
            
            # Próba dopasowania wzorca słówka
            word_match = re.match(word_pattern, line)
            if word_match:
                # Jeśli było poprzednie słówko, dodaj je do listy
                if current_word:
                    words.append(current_word)
                
                # Wyciąganie tłumaczenia polskiego
                polish_text = word_match.group(4).strip()
                
                # Jeśli w tłumaczeniu jest "ex:" to znaczy że przykład jest w tej samej linii
                # Odcinamy go
                if 'ex:' in polish_text.lower():
                    # Znajdujemy pozycję "ex:" (case-insensitive)
                    ex_pos = polish_text.lower().find('ex:')
                    # Tłumaczenie to część przed "ex:"
                    actual_polish = polish_text[:ex_pos].strip()
                    # Przykład to część po "ex:"
                    example_text = polish_text[ex_pos+3:].strip()
                else:
                    actual_polish = polish_text
                    example_text = None
                
                # Tworzenie nowego słówka
                current_word = {
                    'number': int(word_match.group(1)),
                    'english': word_match.group(2).strip(),
                    'pronunciation': word_match.group(3).strip(),
                    'polish': actual_polish,
                    'example': example_text,
                    'category': current_category
                }
                
                continue
            
            # Próba dopasowania przykładu
            example_match = re.match(example_pattern, line, re.IGNORECASE)
            if example_match and current_word:
                current_word['example'] = example_match.group(1).strip()
                continue
            
            # Jeśli linia zaczyna się od "ex:"
            if line.lower().startswith('ex:') and current_word:
                current_word['example'] = line[3:].strip()
        
        # Dodanie ostatniego słówka
        if current_word:
            words.append(current_word)
        
        return words
    
    def extract_word_list(self, words: list) -> list:
        """
        Wyciąga samą listę słówek angielskich
        
        Args:
            words: Lista słowników ze słówkami
            
        Returns:
            Lista słówek angielskich (stringów)
        """
        return [word['english'].lower() for word in words if word.get('english')]
    
    def format_words_for_display(self, words: list) -> str:
        """
        Formatuje listę słówek do wyświetlenia
        
        Args:
            words: Lista słowników ze słówkami
            
        Returns:
            Sformatowany tekst do wyświetlenia
        """
        # Grupowanie słówek według kategorii
        categories = {}
        for word in words:
            category = word.get('category', 'INNE')
            if category not in categories:
                categories[category] = []
            categories[category].append(word)
        
        # Formatowanie tekstu
        result = []
        
        for category, cat_words in categories.items():
            if category:
                result.append(f"\n**{category}**\n")
            
            for word in cat_words:
                # Format: numer. słówko (wymowa) – tłumaczenie
                line = f"{word['number']}. **{word['english']}** ({word['pronunciation']}) – {word['polish']}"
                result.append(line)
                
                # Dodanie przykładu jeśli istnieje
                if word.get('example'):
                    result.append(f"   *ex: {word['example']}*")
        
        return "\n".join(result)
