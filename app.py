# -*- coding: utf-8 -*-
"""
Aplikacja do nauki słówek angielskich
=====================================
Główny plik aplikacji Streamlit

Funkcje:
- Generowanie list słówek z pomocą AI
- Eksport do plików Word
- Konwersja na audio MP3
- Zarządzanie plikami w bazie danych
"""

# ============================================================
# IMPORTOWANIE BIBLIOTEK
# ============================================================

# Biblioteka do tworzenia interfejsu webowego
import streamlit as st

# Biblioteka do ładowania zmiennych środowiskowych
from dotenv import load_dotenv
import os

# Biblioteki do operacji na plikach
from io import BytesIO
from datetime import datetime

# Importowanie modułów pomocniczych
from utils.openai_helper import OpenAIHelper
from utils.word_generator import WordGenerator
from utils.audio_generator import AudioGenerator
from utils.database import DatabaseManager
from utils.word_parser import WordParser

# Importowanie konfiguracji
from config import (
    AVAILABLE_VOICES, 
    DEFAULT_VOICE,
    DEFAULT_AUDIO_SETTINGS,
    GENERATION_PROMPT_TEMPLATE
)

# ============================================================
# ŁADOWANIE KONFIGURACJI
# ============================================================

# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# ============================================================
# KONFIGURACJA STRONY STREAMLIT
# ============================================================

# Ustawienia strony (tytuł, ikona, layout)
st.set_page_config(
    page_title="Angielskie Słówka - Generator",  # Tytuł w zakładce przeglądarki
    page_icon="📚",                               # Ikona w zakładce
    layout="wide"                                 # Szeroki layout
)

# ============================================================
# INICJALIZACJA SESJI
# ============================================================

# Inicjalizacja zmiennych sesji (przechowują stan między odświeżeniami)
if 'conversation_history' not in st.session_state:
    # Historia konwersacji z AI
    st.session_state.conversation_history = []

if 'generated_words_text' not in st.session_state:
    # Tekst wygenerowanych słówek
    st.session_state.generated_words_text = None

if 'generated_doc' not in st.session_state:
    # Wygenerowany dokument Word
    st.session_state.generated_doc = None

if 'openai_api_key' not in st.session_state:
    # Klucz API OpenAI (może być z .env lub wprowadzony ręcznie)
    st.session_state.openai_api_key = os.getenv('OPENAI_API_KEY', '')

if 'do_spaces_config' not in st.session_state:
    # Konfiguracja DigitalOcean Spaces
    st.session_state.do_spaces_config = {
        'endpoint': os.getenv('DO_SPACES_ENDPOINT', ''),
        'region': os.getenv('DO_SPACES_REGION', ''),
        'bucket': os.getenv('DO_SPACES_BUCKET', ''),
        'folder': os.getenv('DO_SPACES_FOLDER', ''),
        'access_key': os.getenv('DO_SPACES_KEY', ''),
        'secret_key': os.getenv('DO_SPACES_SECRET', '')
    }

# ============================================================
# FUNKCJE POMOCNICZE
# ============================================================

def get_openai_helper():
    """
    Zwraca instancję OpenAIHelper lub None jeśli brak klucza API
    """
    # Sprawdzenie czy klucz API jest dostępny
    api_key = st.session_state.openai_api_key
    if not api_key:
        return None
    return OpenAIHelper(api_key)

def get_database_manager():
    """
    Zwraca instancję DatabaseManager lub None jeśli brak konfiguracji
    """
    # Sprawdzenie czy konfiguracja DigitalOcean Spaces jest dostępna
    config = st.session_state.do_spaces_config
    # Folder jest opcjonalny, więc sprawdzamy tylko podstawowe dane
    required_fields = ['endpoint', 'region', 'bucket', 'access_key', 'secret_key']
    if not all(config.get(field) for field in required_fields):
        return None
    return DatabaseManager(
        endpoint=config['endpoint'],
        region=config['region'],
        bucket=config['bucket'],
        access_key=config['access_key'],
        secret_key=config['secret_key'],
        folder=config.get('folder', '')
    )

def display_chat_message(role: str, content: str):
    """
    Wyświetla wiadomość w stylu czatu
    
    Args:
        role: 'user' lub 'assistant'
        content: Treść wiadomości
    """
    # Wybór ikony w zależności od roli
    if role == "user":
        avatar = "👤"
    else:
        avatar = "🤖"
    
    # Wyświetlenie wiadomości
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

# ============================================================
# SPRAWDZANIE KLUCZA API
# ============================================================

def check_api_key():
    """
    Sprawdza czy klucz API OpenAI jest dostępny
    Jeśli nie, wyświetla pole do wprowadzenia
    
    Returns:
        True jeśli klucz jest dostępny, False w przeciwnym razie
    """
    # Sprawdzenie czy klucz jest już zapisany
    if st.session_state.openai_api_key:
        return True
    
    # Wyświetlenie informacji o braku klucza
    st.warning("⚠️ Nie znaleziono klucza API OpenAI w pliku .env")
    
    # Pole do wprowadzenia klucza
    api_key = st.text_input(
        "Wprowadź klucz API OpenAI:",
        type="password",  # Ukrycie wprowadzanego tekstu
        help="Klucz API znajdziesz na stronie platform.openai.com"
    )
    
    # Przycisk do zapisania klucza
    if st.button("Zapisz klucz API"):
        if api_key:
            # Zapisanie klucza w sesji
            st.session_state.openai_api_key = api_key
            st.success("✅ Klucz API został zapisany!")
            st.rerun()  # Odświeżenie strony
        else:
            st.error("❌ Wprowadź poprawny klucz API")
    
    return False

# ============================================================
# ZAKŁADKA 1: GENEROWANIE SŁÓWEK
# ============================================================

def tab_generate_words():
    """
    Zakładka do generowania słówek z pomocą AI
    """
    st.header("🎓 Generowanie słówek")
    
    # Sprawdzenie klucza API
    if not check_api_key():
        return
    
    # Inicjalizacja helperów
    openai_helper = get_openai_helper()
    db_manager = get_database_manager()
    word_generator = WordGenerator()
    
    # --------------------------------------------------------
    # SEKCJA: GENEROWANIE LISTY SŁÓWEK
    # --------------------------------------------------------
    st.subheader("📝 Generowanie listy słówek")
    
    # Dwie kolumny dla ustawień
    col1, col2 = st.columns(2)
    
    with col1:
        # Pole na temat słówek
        topic = st.text_input(
            "Temat słówek:",
            placeholder="np. podróże, biznes, jedzenie...",
            help="Opisz tematykę słówek do wygenerowania"
        )
    
    with col2:
        # Liczba słówek do wygenerowania
        word_count = st.number_input(
            "Liczba słówek:",
            min_value=5,
            max_value=50,
            value=20,
            help="Ile słówek wygenerować (5-50)"
        )
    
    # Przycisk do generowania
    if st.button("🚀 Generuj listę słówek", type="primary"):
        if not topic:
            st.error("❌ Wprowadź temat słówek")
        else:
            # Pobieranie historii słówek z bazy danych
            existing_words = []
            if db_manager:
                with st.spinner("📚 Pobieranie historii słówek..."):
                    existing_words = db_manager.get_words_history()
            
            # Formatowanie listy istniejących słówek
            if existing_words:
                existing_words_text = ", ".join(existing_words[:100])  # Max 100 słówek w prompt
                if len(existing_words) > 100:
                    existing_words_text += f" ... (i {len(existing_words) - 100} więcej)"
            else:
                existing_words_text = "Brak wcześniejszych słówek"
            
            # Tworzenie promptu do generowania
            generation_prompt = GENERATION_PROMPT_TEMPLATE.format(
                count=word_count,
                topic=topic,
                existing_words=existing_words_text
            )
            
            # Generowanie słówek
            with st.spinner("✨ Generuję słówka..."):
                generated_text = openai_helper.generate_words(generation_prompt)
            
            # Zapisanie wygenerowanego tekstu w sesji
            st.session_state.generated_words_text = generated_text
            
            # Parsowanie słówek
            parser = WordParser()
            words = parser.parse_text(generated_text)
            word_list = parser.extract_word_list(words)
            
            # Zapisywanie do bazy danych
            if db_manager and word_list:
                with st.spinner("💾 Zapisuję do bazy danych..."):
                    db_manager.add_words_to_history(word_list)
            
            # Generowanie dokumentu Word
            with st.spinner("📄 Tworzę dokument Word..."):
                doc_buffer = word_generator.create_document(generated_text, topic)
                st.session_state.generated_doc = doc_buffer
            
            # Zapisywanie dokumentu do DigitalOcean Spaces
            if db_manager:
                with st.spinner("☁️ Zapisuję dokument w chmurze..."):
                    try:
                        # Tworzymy kopię bufora, aby nie zamknąć oryginalnego
                        doc_buffer.seek(0)
                        doc_copy = BytesIO(doc_buffer.read())
                        doc_buffer.seek(0)  # Resetujemy pozycję oryginalnego bufora
                        db_manager.save_word_document(doc_copy, topic)
                    except Exception as e:
                        st.warning(f"⚠️ Nie udało się zapisać w chmurze: {e}")
            
            st.success(f"✅ Wygenerowano {len(words)} słówek!")
    
    # --------------------------------------------------------
    # SEKCJA: PODGLĄD I POBIERANIE WYGENEROWANYCH SŁÓWEK
    # --------------------------------------------------------
    if st.session_state.generated_words_text:
        st.divider()
        st.subheader("📋 Wygenerowane słówka")
        
        # Wyświetlenie słówek w rozwijanym panelu
        with st.expander("Zobacz wygenerowane słówka", expanded=True):
            st.markdown(st.session_state.generated_words_text)
        
        # Przycisk do pobrania dokumentu Word
        if st.session_state.generated_doc:
            # Reset pozycji bufora
            st.session_state.generated_doc.seek(0)
            
            # Generowanie nazwy pliku według schematu: Słówka rr.mm.dd
            date_str = datetime.now().strftime("%y.%m.%d")
            filename = f"Słówka {date_str}.docx"
            
            st.download_button(
                label="📥 Pobierz plik Word",
                data=st.session_state.generated_doc,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        
        # --------------------------------------------------------
        # SEKCJA: KONWERSJA NA AUDIO
        # --------------------------------------------------------
        st.divider()
        st.subheader("🎧 Konwersja na audio")
        
        # Ustawienia audio w kolumnach
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Szybkość mowy
            speed = st.slider(
                "Szybkość mowy:",
                min_value=0.5,
                max_value=2.0,
                value=DEFAULT_AUDIO_SETTINGS['speed'],
                step=0.1,
                help="0.5 = wolno, 1.0 = normalnie, 2.0 = szybko"
            )
            
            # Głos lektora
            voice = st.selectbox(
                "Głos lektora:",
                options=list(AVAILABLE_VOICES.keys()),
                format_func=lambda x: AVAILABLE_VOICES[x],
                index=list(AVAILABLE_VOICES.keys()).index(DEFAULT_VOICE)
            )
        
        with col2:
            # Przerwa między hasłami
            pause_between = st.slider(
                "Przerwa między hasłami (s):",
                min_value=0.5,
                max_value=5.0,
                value=DEFAULT_AUDIO_SETTINGS['pause_between'],
                step=0.5,
                help="Czas przerwy między kolejnymi słówkami"
            )
            
            # Liczba powtórzeń
            repetitions = st.selectbox(
                "Liczba powtórzeń hasła:",
                options=[1, 2],
                index=0,
                help="Ile razy powtórzyć każde słówko"
            )
        
        with col3:
            # Czy czytać przykłady
            include_examples = st.checkbox(
                "Czytaj przykładowe zdania",
                value=DEFAULT_AUDIO_SETTINGS['include_examples'],
                help="Czy lektor ma czytać zdania przykładowe"
            )
            
            # Tryb testu
            test_mode = st.selectbox(
                "Tryb nauki:",
                options=[
                    ("Normalny (angielski → polski)", None),
                    ("Test: polski → angielski", "pl_to_en"),
                    ("Test: angielski → polski", "en_to_pl")
                ],
                format_func=lambda x: x[0],
                help="Wybierz tryb nauki"
            )[1]  # Pobieramy drugą wartość krotki (tryb)
        
        # Przycisk do generowania audio
        if st.button("🎤 Generuj plik audio", type="primary"):
            # Parsowanie słówek
            parser = WordParser()
            words = parser.parse_text(st.session_state.generated_words_text)
            
            if not words:
                st.error("❌ Nie znaleziono słówek do konwersji")
            else:
                # Ustawienia audio
                audio_settings = {
                    'speed': speed,
                    'pause_between': pause_between,
                    'repetitions': repetitions,
                    'include_examples': include_examples,
                    'test_mode': test_mode,
                    'voice': voice
                }
                
                # Generowanie audio
                with st.spinner("🎵 Generuję audio... Proszę czekać."):
                    try:
                        audio_generator = AudioGenerator(openai_helper)
                        audio_buffer = audio_generator.generate_audio(words, audio_settings)
                        
                        # Pobranie danych audio
                        audio_data = audio_buffer.getvalue()
                        
                        # Debug - sprawdzenie rozmiaru
                        print(f"\n[APP] Rozmiar audio: {len(audio_data)} bajtów")
                        
                        if len(audio_data) == 0:
                            st.error("❌ Wygenerowane audio ma 0 bajtów - sprawdź logi terminala")
                        else:
                            # Zapisanie audio w sesji do odtwarzania
                            st.session_state.generated_audio = audio_data
                            
                            st.success(f"✅ Audio zostało wygenerowane! ({len(audio_data)} bajtów)")
                            st.rerun()  # Odświeżenie strony aby pokazać odtwarzacz
                        
                    except Exception as e:
                        st.error(f"❌ Błąd generowania audio: {e}")
                        import traceback
                        print(f"\n[APP ERROR] {traceback.format_exc()}")
        
        # Wyświetlenie odtwarzacza i przycisku pobierania jeśli audio zostało wygenerowane
        if 'generated_audio' in st.session_state and st.session_state.generated_audio:
            st.divider()
            st.subheader("🎧 Wygenerowane audio")
            
            # Odtwarzacz audio
            st.audio(st.session_state.generated_audio, format="audio/mp3")
            
            # Przycisk do pobrania pliku
            date_str = datetime.now().strftime("%y.%m.%d")
            audio_filename = f"Słówka {date_str}.mp3"
            
            st.download_button(
                label="📥 Pobierz plik MP3",
                data=st.session_state.generated_audio,
                file_name=audio_filename,
                mime="audio/mpeg"
            )
    
    # Przycisk do czyszczenia konwersacji
    if st.session_state.conversation_history:
        st.divider()
        if st.button("🗑️ Wyczyść konwersację"):
            st.session_state.conversation_history = []
            st.session_state.generated_words_text = None
            st.session_state.generated_doc = None
            st.rerun()

# ============================================================
# ZAKŁADKA 2: KONWERSJA WŁASNEGO PLIKU
# ============================================================

def tab_convert_file():
    """
    Zakładka do konwersji własnych plików Word na audio
    """
    st.header("📂 Konwersja własnego pliku")
    
    # Sprawdzenie klucza API
    if not check_api_key():
        return
    
    # Inicjalizacja helperów
    openai_helper = get_openai_helper()
    db_manager = get_database_manager()
    
    # --------------------------------------------------------
    # SEKCJA: UPLOAD PLIKU
    # --------------------------------------------------------
    st.subheader("📤 Wgraj plik Word ze słówkami")
    
    # Pole do uploadu pliku
    uploaded_file = st.file_uploader(
        "Wybierz plik .docx",
        type=['docx'],
        help="Wgraj plik Word z listą słówek w odpowiednim formacie"
    )
    
    if uploaded_file:
        # Odczytanie pliku
        file_data = BytesIO(uploaded_file.read())
        
        # Parsowanie dokumentu
        parser = WordParser()
        
        try:
            words = parser.parse_document(file_data)
            
            if not words:
                st.error("❌ Nie znaleziono słówek w pliku. Sprawdź format.")
            else:
                st.success(f"✅ Znaleziono {len(words)} słówek")
                
                # Zapisywanie do historii słówek
                if db_manager:
                    word_list = parser.extract_word_list(words)
                    if word_list:
                        with st.spinner("💾 Zapisuję do historii..."):
                            try:
                                db_manager.add_words_to_history(word_list)
                                st.info("📝 Słówka zostały dodane do historii")
                            except Exception as e:
                                st.warning(f"⚠️ Nie udało się zapisać do historii: {e}")
                
                # Podgląd słówek
                with st.expander("Zobacz znalezione słówka"):
                    formatted = parser.format_words_for_display(words)
                    st.markdown(formatted)
                
                # --------------------------------------------------------
                # SEKCJA: USTAWIENIA AUDIO
                # --------------------------------------------------------
                st.divider()
                st.subheader("🎧 Ustawienia konwersji audio")
                
                # Ustawienia w kolumnach
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    speed = st.slider(
                        "Szybkość mowy:",
                        min_value=0.5,
                        max_value=2.0,
                        value=1.0,
                        step=0.1,
                        key="convert_speed"
                    )
                    
                    voice = st.selectbox(
                        "Głos lektora:",
                        options=list(AVAILABLE_VOICES.keys()),
                        format_func=lambda x: AVAILABLE_VOICES[x],
                        index=list(AVAILABLE_VOICES.keys()).index(DEFAULT_VOICE),
                        key="convert_voice"
                    )
                
                with col2:
                    pause_between = st.slider(
                        "Przerwa między hasłami (s):",
                        min_value=0.5,
                        max_value=5.0,
                        value=2.0,
                        step=0.5,
                        key="convert_pause"
                    )
                    
                    repetitions = st.selectbox(
                        "Liczba powtórzeń:",
                        options=[1, 2],
                        index=0,
                        key="convert_repetitions"
                    )
                
                with col3:
                    include_examples = st.checkbox(
                        "Czytaj przykłady",
                        value=True,
                        key="convert_examples"
                    )
                    
                    test_mode = st.selectbox(
                        "Tryb nauki:",
                        options=[
                            ("Normalny", None),
                            ("Test: PL → EN", "pl_to_en"),
                            ("Test: EN → PL", "en_to_pl")
                        ],
                        format_func=lambda x: x[0],
                        key="convert_test_mode"
                    )[1]
                
                # Przycisk do generowania
                if st.button("🎤 Konwertuj na audio", type="primary", key="convert_btn"):
                    audio_settings = {
                        'speed': speed,
                        'pause_between': pause_between,
                        'repetitions': repetitions,
                        'include_examples': include_examples,
                        'test_mode': test_mode,
                        'voice': voice
                    }
                    
                    with st.spinner("🎵 Generuję audio... Proszę czekać."):
                        try:
                            audio_generator = AudioGenerator(openai_helper)
                            audio_buffer = audio_generator.generate_audio(words, audio_settings)
                            
                            # Zapisanie audio w sesji
                            st.session_state.converted_audio = audio_buffer.getvalue()
                            st.success("✅ Audio zostało wygenerowane!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Błąd: {e}")
                
                # Wyświetlenie odtwarzacza jeśli audio zostało wygenerowane
                if 'converted_audio' in st.session_state and st.session_state.converted_audio:
                    st.divider()
                    st.subheader("🎧 Wygenerowane audio")
                    
                    # Odtwarzacz audio
                    st.audio(st.session_state.converted_audio, format="audio/mp3")
                    
                    # Nazwa pliku według schematu: Słówka rr.mm.dd
                    date_str = datetime.now().strftime("%y.%m.%d")
                    audio_filename = f"Słówka {date_str}.mp3"
                    
                    st.download_button(
                        label="📥 Pobierz plik MP3",
                        data=st.session_state.converted_audio,
                        file_name=audio_filename,
                        mime="audio/mpeg"
                    )
                            
        except Exception as e:
            st.error(f"❌ Błąd odczytu pliku: {e}")

# ============================================================
# ZAKŁADKA 3: ZARZĄDZANIE PLIKAMI
# ============================================================

def tab_manage_files():
    """
    Zakładka do zarządzania plikami w bazie danych
    """
    st.header("📁 Zarządzanie plikami")
    
    # Inicjalizacja managera bazy danych
    db_manager = get_database_manager()
    
    if not db_manager:
        st.warning("⚠️ Nie skonfigurowano połączenia z DigitalOcean Spaces")
        st.info("Uzupełnij dane dostępowe DigitalOcean Spaces w pliku .env")
        return
    
    # Pobieranie listy plików
    with st.spinner("📂 Pobieranie listy plików..."):
        try:
            files = db_manager.list_files()
        except Exception as e:
            st.error(f"❌ Błąd pobierania plików: {e}")
            
            # Pomocne wskazówki diagnostyczne
            with st.expander("🔍 Diagnostyka problemu"):
                st.write("**Sprawdź konfigurację w pliku .env:**")
                st.code(f"""
DO_SPACES_ENDPOINT={st.session_state.do_spaces_config['endpoint']}
DO_SPACES_REGION={st.session_state.do_spaces_config['region']}
DO_SPACES_BUCKET={st.session_state.do_spaces_config['bucket']}
DO_SPACES_KEY=***
DO_SPACES_SECRET=***
                """, language="env")
                st.write("**Upewnij się, że:**")
                st.write("- Bucket istnieje w DigitalOcean Spaces")
                st.write("- Endpoint NIE zawiera nazwy bucketa (tylko region)")
                st.write("- Klucze dostępowe są prawidłowe")
            return
    
    if not files:
        st.info("📭 Brak zapisanych plików")
        st.write("Wygeneruj słówka w zakładce 'Generowanie słówek', aby utworzyć pierwszy plik.")
        return
    
    # Filtrowanie tylko plików .docx
    word_files = [f for f in files if f.get('pathname', '').endswith('.docx')]
    
    st.success(f"📚 Znaleziono {len(word_files)} plików Word")
    
    # Wyświetlenie listy plików
    for file in word_files:
        # Tworzenie karty dla każdego pliku
        with st.expander(f"📄 {file.get('pathname', 'Nieznany plik')}"):
            # Informacje o pliku
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Data utworzenia
                uploaded_at = file.get('uploadedAt', 'Nieznana')
                st.write(f"**Data dodania:** {uploaded_at}")
                
                # Rozmiar pliku
                size = file.get('size', 0)
                size_kb = size / 1024
                st.write(f"**Rozmiar:** {size_kb:.1f} KB")
            
            with col2:
                # Przycisk do pobrania
                file_key = file.get('key', '')
                file_url = file.get('url', '')
                if file_key:
                    try:
                        # Pobieranie pliku
                        file_data = db_manager.download_file(file_key)
                        
                        st.download_button(
                            label="📥 Pobierz",
                            data=file_data,
                            file_name=file.get('pathname', 'plik.docx'),
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"download_{file.get('pathname')}"
                        )
                    except Exception as e:
                        st.error(f"Błąd: {e}")
                
                # Przycisk do usunięcia
                if st.button("🗑️ Usuń", key=f"delete_{file.get('pathname')}"):
                    if db_manager.delete_file(file_key):
                        st.success("✅ Plik usunięty")
                        st.rerun()
                    else:
                        st.error("❌ Błąd usuwania")
            
            # Podgląd zawartości
            if file_key:
                if st.button("👁️ Podgląd zawartości", key=f"preview_{file.get('pathname')}"):
                    try:
                        file_data = db_manager.download_file(file_key)
                        parser = WordParser()
                        words = parser.parse_document(file_data)
                        
                        if words:
                            formatted = parser.format_words_for_display(words)
                            st.markdown(formatted)
                        else:
                            st.info("Brak słówek do wyświetlenia")
                    except Exception as e:
                        st.error(f"Błąd podglądu: {e}")
    
    # --------------------------------------------------------
    # SEKCJA: STATYSTYKI
    # --------------------------------------------------------
    st.divider()
    st.subheader("📊 Statystyki")
    
    # Pobieranie historii słówek
    words_history = db_manager.get_words_history()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Liczba plików Word", len(word_files))
    
    with col2:
        st.metric("Wszystkie słówka w historii", len(words_history))
    
    # Lista wszystkich słówek
    if words_history:
        with st.expander("📝 Zobacz wszystkie słówka w historii"):
            # Wyświetlenie słówek w kolumnach
            cols = st.columns(4)
            for i, word in enumerate(sorted(words_history)):
                cols[i % 4].write(f"• {word}")

# ============================================================
# GŁÓWNA FUNKCJA APLIKACJI
# ============================================================

def main():
    """
    Główna funkcja uruchamiająca aplikację
    """
    # Tytuł aplikacji
    st.title("📚 Generator Słówek Angielskich")
    st.caption("Aplikacja do nauki słówek z pomocą AI")
    
    # Tworzenie zakładek
    tab1, tab2, tab3 = st.tabs([
        "🎓 Generowanie słówek",
        "📂 Konwersja pliku",
        "📁 Zarządzanie plikami"
    ])
    
    # Zawartość zakładek
    with tab1:
        tab_generate_words()
    
    with tab2:
        tab_convert_file()
    
    with tab3:
        tab_manage_files()

# ============================================================
# URUCHOMIENIE APLIKACJI
# ============================================================

# Uruchomienie głównej funkcji gdy skrypt jest wykonywany bezpośrednio
if __name__ == "__main__":
    main()
