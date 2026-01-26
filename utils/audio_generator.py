# -*- coding: utf-8 -*-
"""
Moduł do generowania plików audio MP3 z listy słówek
Wykorzystuje OpenAI TTS + FFmpeg do łączenia plików
Każde hasło generowane osobno - eliminuje halucynacje TTS
BEZ PYDUB - bezpośrednio FFmpeg concat
"""

from io import BytesIO
import tempfile
import os
import subprocess
import shutil

from config import DEFAULT_VOICE, TEST_PAUSE_DURATION

# Znajdź FFmpeg - preferuj wersję z winget (ma libmp3lame)
FFMPEG_PATH = None
possible_paths = [
    r"C:\Users\Lukasz\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe",
    shutil.which("ffmpeg"),
    r"C:\conda\envs\od_zera_do_ai\Library\bin\ffmpeg.exe"
]

for path in possible_paths:
    if path and os.path.exists(path):
        FFMPEG_PATH = path
        break

if not FFMPEG_PATH:
    FFMPEG_PATH = "ffmpeg"  # Fallback

print(f"[AUDIO] FFmpeg: {FFMPEG_PATH}")


class AudioGenerator:
    """
    Klasa do generowania plików audio z listy słówek
    Używa FFmpeg do łączenia plików MP3 (bez pydub)
    """
    
    def __init__(self, openai_helper):
        self.openai = openai_helper
        self._temp_dir = None
        self._file_counter = 0
    
    def generate_audio(self, words: list, settings: dict) -> BytesIO:
        """Generuje plik audio MP3 z listy słówek"""
        speed = settings.get('speed', 1.0)
        pause_between = settings.get('pause_between', 2.0)
        repetitions = settings.get('repetitions', 1)
        include_examples = settings.get('include_examples', True)
        test_mode = settings.get('test_mode', None)
        voice = settings.get('voice', DEFAULT_VOICE)
        
        print(f"\n=== GENEROWANIE AUDIO ===")
        print(f"Liczba haseł: {len(words)}")
        print(f"Przerwa między hasłami: {pause_between}s")
        
        # Katalog tymczasowy na pliki MP3
        self._temp_dir = tempfile.mkdtemp(prefix="audio_")
        self._file_counter = 0
        
        # Lista plików do połączenia
        file_list = []
        
        try:
            # Generowanie ciszy (przerwy)
            silence_1s_path = self._generate_silence(1.0)
            silence_between_path = self._generate_silence(pause_between)
            silence_test_path = self._generate_silence(TEST_PAUSE_DURATION)
            
            # Przetwarzanie każdego hasła
            for i, word in enumerate(words, 1):
                english = (word.get('english') or '').strip()
                polish = (word.get('polish') or '').strip()
                example = (word.get('example') or '').strip()
                
                if not english or not polish:
                    continue
                
                # Czyszczenie
                if '(' in english:
                    english = english.split('(')[0].strip()
                
                print(f"\n[{i}/{len(words)}] Hasło #{word.get('number', i)}:")
                print(f"  EN: '{english}'")
                print(f"  PL: '{polish}'")
                
                # Generowanie audio dla hasła
                word_files = self._generate_word_files(
                    english, polish, example,
                    include_examples, test_mode,
                    speed, voice,
                    silence_1s_path, silence_test_path
                )
                
                # Powtórzenia
                for rep in range(repetitions):
                    file_list.extend(word_files)
                    if rep < repetitions - 1:
                        file_list.append(silence_1s_path)
                
                # Przerwa między hasłami (oprócz ostatniego)
                if i < len(words):
                    file_list.append(silence_between_path)
            
            print(f"\n=== ŁĄCZENIE {len(file_list)} PLIKÓW ===")
            
            # Łączenie plików przez FFmpeg
            output_path = os.path.join(self._temp_dir, "output.mp3")
            self._concat_files(file_list, output_path)
            
            # Wczytanie wyniku
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"✅ Wynik: {file_size} bajtów ({file_size/1024:.1f} KB)")
                
                buffer = BytesIO()
                with open(output_path, 'rb') as f:
                    buffer.write(f.read())
                buffer.seek(0)
                return buffer
            else:
                print("❌ Nie utworzono pliku wyjściowego")
                return BytesIO()
                
        finally:
            # Czyszczenie plików tymczasowych
            self._cleanup()
    
    def _generate_silence(self, duration_sec: float) -> str:
        """Generuje plik ciszy o zadanej długości"""
        self._file_counter += 1
        path = os.path.join(self._temp_dir, f"silence_{self._file_counter}.mp3")
        
        # FFmpeg generuje ciszę
        cmd = [
            FFMPEG_PATH, '-y',
            '-f', 'lavfi',
            '-i', f'anullsrc=r=24000:cl=mono',
            '-t', str(duration_sec),
            '-acodec', 'libmp3lame',
            '-b:a', '128k',
            path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[SILENCE] Błąd (kod {result.returncode}): {result.stderr[:200]}")
        else:
            size = os.path.getsize(path) if os.path.exists(path) else 0
            print(f"[SILENCE] {duration_sec}s -> {size} B")
        
        return path
    
    def _generate_word_files(self, english, polish, example,
                              include_examples, test_mode, speed, voice,
                              silence_1s, silence_test) -> list:
        """Generuje pliki MP3 dla jednego hasła"""
        files = []
        
        if test_mode == "pl_to_en":
            # Polski -> pauza -> angielski
            files.append(self._text_to_file(polish, speed, voice))
            files.append(silence_test)
            files.append(self._text_to_file(english, speed, voice))
            
        elif test_mode == "en_to_pl":
            # Angielski -> pauza -> polski
            files.append(self._text_to_file(english, speed, voice))
            files.append(silence_test)
            files.append(self._text_to_file(polish, speed, voice))
            
        else:
            # Normalny: angielski -> 1s -> polski -> 1s -> przykład
            files.append(self._text_to_file(english, speed, voice))
            files.append(silence_1s)
            files.append(self._text_to_file(polish, speed, voice))
            
            if include_examples and example:
                files.append(silence_1s)
                files.append(self._text_to_file(example, speed, voice))
        
        return files
    
    def _text_to_file(self, text: str, speed: float, voice: str) -> str:
        """Konwertuje tekst na plik MP3 przez OpenAI TTS"""
        self._file_counter += 1
        path = os.path.join(self._temp_dir, f"audio_{self._file_counter}.mp3")
        
        # Konwersja przez OpenAI TTS
        audio_bytes = self.openai.text_to_speech(text, voice=voice, speed=speed)
        
        with open(path, 'wb') as f:
            f.write(audio_bytes)
        
        size = os.path.getsize(path)
        print(f"[TTS] '{text[:25]}...' -> {size} B")
        
        return path
    
    def _concat_files(self, file_list: list, output_path: str):
        """Łączy pliki MP3 przez FFmpeg concat"""
        # Tworzenie pliku z listą
        list_path = os.path.join(self._temp_dir, "filelist.txt")
        with open(list_path, 'w', encoding='utf-8') as f:
            for file_path in file_list:
                # FFmpeg wymaga slash / nawet na Windows
                safe_path = file_path.replace('\\', '/')
                f.write(f"file '{safe_path}'\n")
        
        # FFmpeg concat
        cmd = [
            FFMPEG_PATH, '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_path,
            '-acodec', 'libmp3lame',
            '-b:a', '128k',
            output_path
        ]
        
        print(f"[FFMPEG] Łączenie plików...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[FFMPEG] BŁĄD (kod {result.returncode}): {result.stderr[-500:]}")
        else:
            print(f"[FFMPEG] OK")
    
    def _cleanup(self):
        """Usuwa pliki tymczasowe"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                print("[CLEANUP] Usunięto pliki tymczasowe")
            except Exception as e:
                print(f"[CLEANUP] Błąd: {e}")
