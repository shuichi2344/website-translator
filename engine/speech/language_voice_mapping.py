"""
Language to TTS Voice Mapping
Maps user-selected languages to appropriate edge-tts voices
"""

# Language to edge-tts voice mapping
LANGUAGE_VOICE_MAP = {
    "English": [
        "en-US-AriaNeural",
        "en-GB-SoniaNeural",
        "en-AU-NatashaNeural",
        "en-US-JennyNeural"
    ],
    "Bahasa Melayu": [
        "ms-MY-YasminNeural",
        "ms-MY-OsmanNeural"
    ],
    "Bahasa Indonesia": [
        "id-ID-GadisNeural",
        "id-ID-ArdiNeural"
    ],
    "Thai": [
        "th-TH-PremwadeeNeural",
        "th-TH-NiwatNeural"
    ],
    "Vietnamese": [
        "vi-VN-HoaiMyNeural",
        "vi-VN-NamMinhNeural"
    ],
    "Filipino/Tagalog": [
        "fil-PH-BlessicaNeural",
        "fil-PH-AngeloNeural"
    ],
    "Burmese": [
        "my-MM-ThiDarNeural",
        "my-MM-NilarNeural"
    ],
    "Khmer": [
        "km-KH-SreymomNeural",
        "km-KH-PisethNeural"
    ],
    "Lao": [
        "lo-LA-KeolaNeural",
        "lo-LA-ChanthavongNeural"
    ],
    "Chinese (Simplified)": [
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural",
        "zh-CN-YunyangNeural"
    ],
    "Tamil": [
        "ta-IN-PallaviNeural",
        "ta-IN-ValluvarNeural"
    ]
}

def get_voices_for_language(language: str) -> list:
    """
    Get list of TTS voices for a given language
    
    Args:
        language: User's selected language (e.g., "English", "Bahasa Melayu")
    
    Returns:
        List of voice names to try (in order of preference)
        Falls back to English if language not found
    """
    voices = LANGUAGE_VOICE_MAP.get(language)
    
    if voices:
        return voices
    
    # Fallback to English
    print(f"⚠️ No voices found for language '{language}', falling back to English")
    return LANGUAGE_VOICE_MAP["English"]

def get_primary_voice(language: str) -> str:
    """
    Get the primary (first) voice for a language
    
    Args:
        language: User's selected language
    
    Returns:
        Primary voice name
    """
    voices = get_voices_for_language(language)
    return voices[0]
