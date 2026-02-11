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
            file_data = self.download_file(history_file['key'])
            
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
