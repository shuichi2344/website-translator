"""
Module Preloader - Loads heavy AI/ML modules during startup
Shows a splash screen while loading to improve perceived performance
"""

import threading
import time
from typing import Callable, Optional

# Global cache for loaded modules
_modules_loaded = False
_modules = {}
_loading_progress = 0
_loading_status = "Initializing..."

def get_loading_progress():
    """Get current loading progress (0-100)"""
    return _loading_progress

def get_loading_status():
    """Get current loading status message"""
    return _loading_status

def preload_modules(progress_callback: Optional[Callable[[int, str], None]] = None):
    """
    Preload all heavy modules during startup
    
    Args:
        progress_callback: Optional callback function(progress: int, status: str)
    """
    global _modules_loaded, _modules, _loading_progress, _loading_status
    
    if _modules_loaded:
        return _modules
    
    def update_progress(progress: int, status: str):
        global _loading_progress, _loading_status
        _loading_progress = progress
        _loading_status = status
        if progress_callback:
            progress_callback(progress, status)
    
    try:
        # Step 1: Load speech recognition (20%)
        update_progress(10, "Loading speech recognition...")
        from engine.speech.speech_to_text import create_session
        _modules['create_session'] = create_session
        update_progress(20, "Speech recognition loaded")
        
        # Step 2: Load voice processing (40%)
        update_progress(25, "Loading voice processing...")
        from engine.speech.main import process_voice_result
        _modules['process_voice_result'] = process_voice_result
        update_progress(40, "Voice processing loaded")
        
        # Step 3: Load text-to-speech (60%)
        update_progress(45, "Loading text-to-speech...")
        from engine.speech.text_to_speech import speak_answer
        _modules['speak_answer'] = speak_answer
        update_progress(60, "Text-to-speech loaded")
        
        # Step 4: Load document summarizer (80%)
        update_progress(65, "Loading AI models...")
        from engine.search.document_summariser_v6_gemini import DocumentSummarizer
        _modules['DocumentSummarizer'] = DocumentSummarizer
        update_progress(80, "AI models loaded")
        
        # Step 5: Load audio transcription (90%)
        update_progress(85, "Loading audio processing...")
        from engine.search.speech_to_text import transcribe_audio
        _modules['transcribe_audio'] = transcribe_audio
        update_progress(90, "Audio processing loaded")
        
        # Step 6: Initialize database connections (100%)
        update_progress(95, "Connecting to database...")
        try:
            from engine.database.auth_handler import AuthHandler
            _modules['AuthHandler'] = AuthHandler
        except Exception as e:
            print(f"Database not available: {e}")
            _modules['AuthHandler'] = None
        
        update_progress(100, "Ready!")
        _modules_loaded = True
        
        return _modules
        
    except Exception as e:
        update_progress(0, f"Error: {e}")
        print(f"Error preloading modules: {e}")
        raise

def get_modules():
    """Get preloaded modules (must call preload_modules first)"""
    return _modules

def is_loaded():
    """Check if modules are loaded"""
    return _modules_loaded
