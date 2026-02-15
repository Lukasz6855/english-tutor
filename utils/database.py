# -*- coding: utf-8 -*-
"""
Moduł do komunikacji z DigitalOcean Spaces
Przechowuje pliki Word oraz historię wygenerowanych słówek
"""

# Importowanie bibliotek boto3 do komunikacji z S3-compatible storage
import boto3
from botocore.exceptions import ClientError
import json

# Importowanie bibliotek do operacji na plikach
from io import BytesIO
from datetime import datetime


class DatabaseManager:
    """
    Klasa do zarządzania bazą danych DigitalOcean Spaces
    Przechowuje pliki Word i historię słówek
    """
    
    def __init__(self, endpoint: str, region: str, bucket: str, access_key: str, secret_key: str, folder: str = ""):
        """
        Inicjalizacja managera bazy danych
        
        Args:
            endpoint: Endpoint DigitalOcean Spaces (np. nyc3.digitaloceanspaces.com)
            region: Region (np. nyc3)
            bucket: Nazwa bucketa
            access_key: Klucz dostępu (Access Key)
            secret_key: Klucz tajny (Secret Key)
            folder: Opcjonalny podfolder w buckecie (np. "english words")
        """
        # Zapisanie konfiguracji
        self.bucket = bucket
        self.endpoint = endpoint
        self.region = region
        
        # Podfolder - usuwamy końcowe / jeśli istnieje i dodamy je przy użyciu
        self.folder = folder.rstrip('/') if folder else ""
        
        # Inicjalizacja klienta S3
        self.s3_client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=f'https://{endpoint}',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        # Nazwa pliku z historią słówek
        self.history_filename = "words_history.json"
    
    def upload_file(self, file_data: BytesIO, filename: str) -> dict:
        """
        Wysyła plik do DigitalOcean Spaces
        
        Args:
            file_data: Dane pliku jako BytesIO
            filename: Nazwa pliku do zapisania
            
        Returns:
            Słownik z informacjami o zapisanym pliku (url, key)
        """
        try:
            # Dodanie prefiksu folderu jeśli jest skonfigurowany
            if self.folder:
                key = f"{self.folder}/{filename}"
            else:
                key = filename
            
            # Przewinięcie bufora na początek
            file_data.seek(0)
            
            # Upload pliku do Spaces
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket,
                key,
                ExtraArgs={'ACL': 'public-read'}  # Publiczny dostęp do odczytu
            )
            
            # Generowanie publicznego URL
            url = f"https://{self.bucket}.{self.endpoint}/{key}"
            
            # Zwrócenie informacji o zapisanym pliku
            return {
                'url': url,
                'key': key,
                'bucket': self.bucket
            }
            
        except ClientError as e:
            raise Exception(f"Błąd podczas uploadu pliku: {e}")
    
    def download_file(self, key: str) -> BytesIO:
        """
        Pobiera plik z DigitalOcean Spaces
        
        Args:
            key: Klucz (nazwa) pliku do pobrania
            
        Returns:
            Dane pliku jako BytesIO
        """
        try:
            # Pobranie pliku z Spaces
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            
            # Zwrócenie danych jako BytesIO
            return BytesIO(response['Body'].read())
            
        except ClientError as e:
            raise Exception(f"Błąd podczas pobierania pliku: {e}")
    
    def list_files(self) -> list:
        """
        Pobiera listę wszystkich plików w DigitalOcean Spaces
        
        Returns:
            Lista słowników z informacjami o plikach
        """
        try:
            # Parametry listowania
            list_params = {'Bucket': self.bucket}
            
            # Jeśli jest skonfigurowany folder, listuj tylko pliki w tym folderze
            if self.folder:
                list_params['Prefix'] = f"{self.folder}/"
            
            # Listowanie obiektów w buckecie
            response = self.s3_client.list_objects_v2(**list_params)
            
            # Sprawdzenie czy są jakieś pliki
            if 'Contents' not in response:
                # Bucket (lub folder) jest pusty
                return []
            
            # Konwersja do formatu kompatybilnego z poprzednią implementacją
            files = []
            for obj in response.get('Contents', []):
                # Generowanie publicznego URL
                url = f"https://{self.bucket}.{self.endpoint}/{obj['Key']}"
                
                # Wyodrębnienie nazwy pliku (bez prefiksu folderu dla czytelności)
                display_name = obj['Key']
                if self.folder and obj['Key'].startswith(f"{self.folder}/"):
                    display_name = obj['Key'][len(self.folder)+1:]
                
                files.append({
                    'key': obj['Key'],
                    'pathname': display_name,
                    'url': url,
                    'size': obj['Size'],
                    'uploadedAt': obj['LastModified'].isoformat()
                })
            
            return files
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', '')
            
            if error_code == 'NoSuchBucket':
                raise Exception(f"Bucket '{self.bucket}' nie istnieje. Upewnij się, że utworzyłeś Space o tej nazwie w DigitalOcean.")
            elif error_code == 'AccessDenied':
                raise Exception(f"Brak dostępu do bucketa '{self.bucket}'. Sprawdź klucze dostępowe (DO_SPACES_KEY/SECRET).")
            elif error_code == 'InvalidAccessKeyId':
                raise Exception("Nieprawidłowy Access Key. Sprawdź wartość DO_SPACES_KEY w .env")
            elif error_code == 'NoSuchKey':
                raise Exception(f"Błąd NoSuchKey - prawdopodobnie nieprawidłowa konfiguracja endpointu. Sprawdź DO_SPACES_ENDPOINT (powinno być '{self.region}.digitaloceanspaces.com', bez nazwy bucketa).")
            else:
                raise Exception(f"Błąd podczas listowania plików ({error_code}): {error_message}")
        except Exception as e:
            if 'ClientError' not in str(type(e)):
                raise Exception(f"Błąd połączenia z DigitalOcean Spaces: {e}. Sprawdź endpoint (DO_SPACES_ENDPOINT='{self.endpoint}') i region (DO_SPACES_REGION='{self.region}').")
            raise
    
    def delete_file(self, key: str) -> bool:
        """
        Usuwa plik z DigitalOcean Spaces
        
        Args:
            key: Klucz (nazwa) pliku do usunięcia
            
        Returns:
            True jeśli usunięcie się powiodło
        """
        try:
            # Usunięcie pliku z Spaces
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            return True
            
        except ClientError as e:
            print(f"Błąd podczas usuwania pliku: {e}")
            return False
    
    def get_words_history(self) -> list:
        """
        Pobiera historię wszystkich wygenerowanych słówek (unikalne słowa ze wszystkich plików)
        
        Returns:
            Lista unikalnych słówek (stringów) które już były wygenerowane
        """
        try:
            # Pobieranie szczegółowej historii
            history_data = self._load_history_file()
            
            if not history_data:
                return []
            
            # Jeśli to stara struktura (lista słówek)
            if 'words' in history_data and isinstance(history_data['words'], list):
                return history_data['words']
            
            # Nowa struktura - zbieramy wszystkie unikalne słówka
            all_words = set()
            for file_data in history_data.get('files', {}).values():
                all_words.update(file_data.get('words', []))
            
            return list(all_words)
            
        except Exception as e:
            # W przypadku błędu zwracamy pustą listę
            print(f"Błąd pobierania historii: {e}")
            return []
    
    def get_history_by_file(self) -> dict:
        """
        Pobiera historię słówek zgrupowaną według plików
        
        Returns:
            Słownik: {filename: {words: [...], created_at: ..., word_count: ...}}
        """
        try:
            history_data = self._load_history_file()
            
            if not history_data:
                return {}
            
            # Jeśli to stara struktura, konwertujemy do nowej
            if 'words' in history_data and isinstance(history_data['words'], list):
                return {}
            
            return history_data.get('files', {})
            
        except Exception as e:
            print(f"Błąd pobierania historii: {e}")
            return {}
    
    def _load_history_file(self) -> dict:
        """
        Wczytuje plik z historią słówek
        
        Returns:
            Słownik z danymi historii lub None jeśli plik nie istnieje
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
            
            # Jeśli nie znaleziono pliku historii
            if not history_file:
                return None
            
            # Pobieranie zawartości pliku historii
            file_data = self.download_file(history_file['key'])
            
            # Parsowanie JSON
            return json.loads(file_data.read().decode('utf-8'))
            
        except Exception as e:
            print(f"Błąd wczytywania pliku historii: {e}")
            return None
    
    def add_words_to_history(self, new_words: list, filename: str) -> bool:
        """
        Dodaje nowe słówka do historii dla konkretnego pliku
        
        Args:
            new_words: Lista nowych słówek do dodania
            filename: Nazwa pliku, do którego należą słówka
            
        Returns:
            True jeśli zapisanie się powiodło
        """
        try:
            # Wczytanie aktualnej historii
            history_data = self._load_history_file()
            
            # Jeśli nie ma historii lub to stara struktura, tworzymy nową
            if not history_data or 'words' in history_data:
                history_data = {'files': {}, 'last_updated': '', 'total_words': 0}
            
            # Normalizacja słówek (małe litery, bez białych znaków)
            normalized_words = [word.lower().strip() for word in new_words if word.strip()]
            
            # Dodanie/aktualizacja danych dla tego pliku
            history_data['files'][filename] = {
                'words': normalized_words,
                'created_at': datetime.now().isoformat(),
                'word_count': len(normalized_words)
            }
            
            # Aktualizacja metadanych
            history_data['last_updated'] = datetime.now().isoformat()
            
            # Obliczenie całkowitej liczby unikalnych słówek
            all_words = set()
            for file_data in history_data['files'].values():
                all_words.update(file_data['words'])
            history_data['total_words'] = len(all_words)
            
            # Konwersja do JSON i BytesIO
            json_str = json.dumps(history_data, ensure_ascii=False, indent=2)
            file_data = BytesIO(json_str.encode('utf-8'))
            
            # Upload pliku historii
            self.upload_file(file_data, self.history_filename)
            
            return True
            
        except Exception as e:
            print(f"Błąd zapisywania historii: {e}")
            return False
    
    def remove_words_from_history(self, filename: str) -> bool:
        """
        Usuwa słówka z historii dla konkretnego pliku.
        Usuwa tylko słówka unikalne dla tego pliku (które nie występują w innych plikach).
        
        Args:
            filename: Nazwa pliku do usunięcia z historii
            
        Returns:
            True jeśli usunięcie się powiodło
        """
        try:
            # Wczytanie aktualnej historii
            history_data = self._load_history_file()
            
            if not history_data or 'files' not in history_data:
                return True  # Nie ma czego usuwać
            
            # Usunięcie pliku z historii
            if filename in history_data['files']:
                del history_data['files'][filename]
            
            # Aktualizacja metadanych
            history_data['last_updated'] = datetime.now().isoformat()
            
            # Obliczenie całkowitej liczby unikalnych słówek
            all_words = set()
            for file_data in history_data['files'].values():
                all_words.update(file_data['words'])
            history_data['total_words'] = len(all_words)
            
            # Konwersja do JSON i BytesIO
            json_str = json.dumps(history_data, ensure_ascii=False, indent=2)
            file_data = BytesIO(json_str.encode('utf-8'))
            
            # Upload pliku historii
            self.upload_file(file_data, self.history_filename)
            
            return True
            
        except Exception as e:
            print(f"Błąd usuwania z historii: {e}")
            return False
    
    def save_word_document(self, doc_data: BytesIO, topic_name: str) -> dict:
        """
        Zapisuje dokument Word z listą słówek używając nazwy opartej na temacie.
        Jeśli plik z takim tematem już istnieje, dodaje numer.
        
        Args:
            doc_data: Dane dokumentu jako BytesIO
            topic_name: Nazwa tematu wygenerowana przez AI
            
        Returns:
            Słownik z informacjami o zapisanym pliku (url, key, filename)
        """
        # Pobieranie listy istniejących plików
        existing_files = self.list_files()
        existing_names = [f.get('pathname', '') for f in existing_files if f.get('pathname', '').endswith('.docx')]
        
        # Generowanie nazwy bazowej
        base_name = f"Słówka - {topic_name}"
        filename = f"{base_name}.docx"
        
        # Sprawdzanie kolizji nazw i dodawanie numeru jeśli potrzeba
        counter = 2
        while filename in existing_names:
            filename = f"{base_name} {counter}.docx"
            counter += 1
        
        # Upload pliku
        result = self.upload_file(doc_data, filename)
        result['filename'] = filename  # Dodajemy nazwę pliku do wyniku
        return result
    
    def test_connection(self) -> bool:
        """
        Testuje połączenie z DigitalOcean Spaces
        
        Returns:
            True jeśli połączenie działa
        """
        try:
            # Próba pobrania listy plików
            self.list_files()
            return True
        except Exception as e:
            print(f"Test połączenia nieudany: {e}")
            return False
            return False
