# text_to_speech.py
import asyncio
import edge_tts
import pygame
import io

# 2026 Recommended Neural Voices for SE Asia
VOICE_MAP = {
    "MY": "ms-MY-YasminNeural", # Malay (Malaysia) - Great for .gov.my
    "SG": "en-SG-LunaNeural",   # English (Singapore)
    "ID": "id-ID-GadisNeural",   # Indonesian (Indonesia)
    "PH": "en-PH-RosaNeural",    # English (Philippines)
    "UK": "en-GB-SoniaNeural",   # English (UK)
    "DEFAULT": "en-US-AriaNeural" # English (US)
}

async def speak_answer(text: str, country_code: str = "SG"):
    """
    Plays the AI's answer using a voice tailored to the user's country.
    """
    # Select voice based on country code, fallback to default
    voice = VOICE_MAP.get(country_code.upper(), VOICE_MAP["DEFAULT"])
    print(f"Using voice: {voice}")

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        if audio_data:
            with io.BytesIO(audio_data) as audio_stream:
                pygame.mixer.music.load(audio_stream)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.1)
    except Exception as e:
        print(f"TTS Error: {e}")