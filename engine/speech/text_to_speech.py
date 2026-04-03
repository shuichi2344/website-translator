import asyncio
import edge_tts
import pygame
import io
from fast_langdetect import detect

# Neural Voices for SE Asia
VOICE_MATRIX = {
    "MY": {
        "en": "en-SG-LunaNeural",      # Local English preference
        "ms": "ms-MY-YasminNeural",    # Malay
        "zh": "zh-CN-XiaoxiaoNeural",  # Mandarin
        "ta": "ta-IN-PallaviNeural"    # Tamil
    },
    "BN": {                            # Brunei
        "ms": "ms-MY-YasminNeural",    # Malay is official
        "en": "en-SG-LunaNeural",      # Regional English preference
        "zh": "zh-CN-XiaoxiaoNeural"
    },
    "TL": {                            # Timor-leste
        "pt": "pt-PT-RaquelNeural",    # Portuguese is an official language
        "en": "en-US-AriaNeural"       # International English fallback
    },
    "SG": {
        "en": "en-SG-LunaNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "ms": "ms-MY-YasminNeural",
        "ta": "ta-IN-PallaviNeural"
    },
    "ID": {
        "id": "id-ID-GadisNeural",     # Indonesian
        "en": "en-ID-MeilaniNeural"    # English with Indo inflection
    },
    "PH": {
        "en": "en-PH-RosaNeural",      # Filipino English
        "tl": "fil-PH-BlessicaNeural"  # Tagalog/Filipino
    },
    "TH": {
        "th": "th-TH-PremwadeeNeural", # Thai
        "en": "en-SG-LunaNeural"       # Fallback to SG English for regional familiarity
    },
    "VN": {
        "vi": "vi-VN-HoaiMyNeural",    # Vietnamese
        "en": "en-US-AriaNeural"
    },
    "MM": {
        "my": "my-MM-ThiDarNeural",    # Burmese (Myanmar)
    },
    "KH": {
        "km": "km-KH-SreymomNeural",   # Khmer (Cambodia)
    },
    "LA": {
        "lo": "lo-LA-KeolaNeural",     # Lao (Laos)
    },
    "DEFAULT": "en-US-AriaNeural"
}

def get_lang(text):
    try:
        # Returns a list like: [{'lang': 'ms', 'score': 0.98}]
        results = detect(text)
        if results and len(results) > 0:
            return results[0]['lang']
        return "en" # Fallback if no language detected
    except Exception as e:
        print(f"Detection Error: {e}")
        return "en"

async def speak_answer(text: str, country_code: str = "DEFAULT"):
    """
    Plays the AI's answer using a voice tailored to the user's country.
    """
    lang = "en"

    try:
        # 2. Attempt detection
        detected = get_lang(text)
        if detected:
            lang = detected
    except Exception as e:
        print(f"Detection Error: {e}. Falling back to 'en'.")

    print(f"Detected language: {lang}")

    # Select voice based on country code, fallback to default
    country_voices = VOICE_MATRIX.get(country_code.upper(), VOICE_MATRIX["DEFAULT"])
    if isinstance(country_voices, str):
        voice = country_voices
    else:
        # Look for the language, then English in that country, then global default string
        voice = country_voices.get(lang, country_voices.get("en", VOICE_MATRIX["DEFAULT"]))

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

if __name__ == "__main__":
    # Test examples (uncomment to test)
    pass
    # # --- MALAYSIA (MY) CONTEXT ---

    # # 1. Local English (Should use en-SG-Luna per your preference)
    # t1 = "Don't forget to renew your road tax before the end of the month, okay?"
    # asyncio.run(speak_answer(t1, "MY"))

    # # 2. Formal Malay (Should use ms-MY-Yasmin)
    # t2 = "Sila pastikan semua dokumen asal dibawa bersama semasa temu janji di pejabat imigresen."
    # asyncio.run(speak_answer(t2, "MY"))

    # # 3. Local Mandarin (Should use zh-SG-Xiaoxiao)
    # t3 = "请记得携带您的身份证，并前往最近的柜台进行登记。"
    # asyncio.run(speak_answer(t3, "MY"))

    # # --- REGIONAL ASEAN CONTEXT ---

    # # 4. Indonesian (Should use id-ID-Gadis)
    # # Scenario: Helping a migrant worker with safety instructions
    # t4 = "Gunakan peralatan keselamatan kerja anda dengan benar untuk menghindari kecelakaan."
    # asyncio.run(speak_answer(t4, "ID"))

    # # 5. Thai (Should use th-TH-Premwadee)
    # # Scenario: Public transport/kiosk greeting
    # t5 = "กรุณารอที่จุดนี้เพื่อรับความช่วยเหลือจากเจ้าหน้าที่ของเรา"
    # asyncio.run(speak_answer(t5, "TH"))

    # # 6. Filipino/Tagalog (Should use fil-PH-Blessica)
    # # Scenario: Healthcare assistance
    # t6 = "Maaari po kayong pumunta sa pinakamalapit na health center para sa inyong libreng check-up."
    # asyncio.run(speak_answer(t6, "PH"))

    # # 7. Vietnamese (Should use vi-VN-HoaiMy)
    # # Scenario: Information for residents
    # t7 = "Vui lòng xuất trình giấy tờ tùy thân của bạn tại quầy tiếp tân để được hỗ trợ."
    # asyncio.run(speak_answer(t7, "VN"))

    # # --- FALLBACK TEST ---

    # # 8. Unrecognized Language / Default (Should fallback to en-US or en-SG)
    # t8 = "Welcome to the digital citizen portal. How can we help you today?"
    # asyncio.run(speak_answer(t8, "XYZ")) # Testing the "DEFAULT" logic

    # # Test 9: Brunei Malay (Using MY voice as local equivalent)
    # # Scenario: Financial assistance instruction
    # t10 = "Sila pastikan borang bantuan kewangan anda lengkap sebelum dihantar."
    # asyncio.run(speak_answer(t10, "BN"))

    # # Test 10: Timor-Leste Portuguese
    # # Scenario: Public health announcement
    # t11 = "Por favor, lave as mãos regularmente para manter a saúde de todos."
    # asyncio.run(speak_answer(t11, "TL"))

    # # Test 11: Malaysian Tamil (Verify ta mapping again)
    # t12 = "உங்கள் வருகைக்கு நன்றி, மீண்டும் வருக."
    # # (Translation: Thank you for your visit, come again.)
    # asyncio.run(speak_answer(t12, "MY"))
