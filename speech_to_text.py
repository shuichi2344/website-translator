import sounddevice as sd
import numpy as np
from pynput import keyboard
from transformers import pipeline

# ==========================
# CONFIGURATION
# ==========================

ASR_MODEL = "mesolitica/malaysian-whisper-small-v2"
LLM_MODEL = "sail/Sailor2-8B-Chat"
SAMPLING_RATE = 16000


# ==========================
# LOAD ASR MODEL
# ==========================

print(f"Loading ASR model: {ASR_MODEL}...")

asr_pipe = pipeline(
    "automatic-speech-recognition",
    model=ASR_MODEL,
    chunk_length_s=30,
    device=-1
)


# ==========================
# LOAD LLM MODEL
# ==========================

print(f"Loading LLM model: {LLM_MODEL} (this may take a while)...")

llm_pipe = pipeline(
    "text-generation",
    model=LLM_MODEL,
    device_map="auto",
    torch_dtype="auto",
)


# ==========================
# DIALECT NORMALIZATION
# ==========================

def normalize_dialect(text):

    system_msg = (
        "You convert spoken Southeast Asian dialect into a concise web search query.\n"
        "Tasks:\n"
        "1. Remove Singlish, Manglish, and dialect expressions.\n"
        "2. Convert the sentence into clear standard English.\n"
        "3. Rewrite it as a short web search query.\n"
        "4. Keep important keywords such as names, numbers, places, and topics.\n"
        "5. Remove filler words like 'can', 'please', 'tell me', 'I want to know'.\n"
        "6. Output ONLY the final search query.\n"
    )

    prompt = f"<|im_start|>system\n{system_msg}<|im_end|>\n<|im_start|>user\nSentence: {text}<|im_end|>\n<|im_start|>assistant\n"

    try:
        output = llm_pipe(
            prompt,
            max_new_tokens=80,
            temperature=0.1,
            return_full_text=False
        )

        if isinstance(output, list) and len(output) > 0:
            result = output[0]["generated_text"]
        else:
            result = str(output)

        return result.strip()

    except Exception as e:
        print(f"❌ LLM error: {e}")
        return text


# ==========================
# PUSH TO TALK SESSION
# ==========================

class PTTSession:

    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.final_text = None

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        if not self.recording:
            print("\n🔴 Recording... (Release SPACE to stop)")
            self.audio_data = []
            self.recording = True

    def stop_recording(self):
        if self.recording:
            self.recording = False
            print("⏹️ Processing...")
            self.process_audio()

    def process_audio(self):

        if not self.audio_data:
            return

        audio_np = np.concatenate(self.audio_data, axis=0).flatten()

        result = asr_pipe(audio_np, generate_kwargs={"task": "transcribe"})
        raw_text = result["text"].strip()

        print(f"\n📝 Raw Transcription: {raw_text}")

        if len(raw_text) < 2:
            print("⚠️ Audio too short to process.")
            return

        print("🧠 Sailor2 Normalizing...")

        improved = normalize_dialect(raw_text)

        self.final_text = improved

        print("-" * 30)
        print(f"✨ Final English: {improved}")
        print("-" * 30)


# ==========================
# MAIN RUN FUNCTION
# ==========================

def speech_to_text():

    session = PTTSession()

    def on_press(key):
        if key == keyboard.Key.space:
            session.start_recording()

    def on_release(key):

        if key == keyboard.Key.space:
            session.stop_recording()

        if key == keyboard.Key.esc:
            print("\nExiting...")
            return False

    stream = sd.InputStream(
        samplerate=SAMPLING_RATE,
        channels=1,
        callback=session.callback
    )

    print("\n🚀 Sailor2 Voice Assistant Ready")
    print("1. Hold [SPACE] to speak")
    print("2. Release [SPACE] to translate to Standard English")
    print("3. Press [ESC] to quit")

    with stream:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    return session.final_text


# ==========================
# DIRECT RUN
# ==========================

if __name__ == "__main__":
    run_speech_to_text()
