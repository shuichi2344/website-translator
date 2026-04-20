import sounddevice as sd
import numpy as np
from pynput import keyboard
from transformers import pipeline
import warnings
import torch
from llama_cpp import Llama
from engine.gpu_accelerator import get_device_for_transformers, get_torch_dtype

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

country = "Malaysia"

# ==========================
# CONFIGURATION
# ==========================
ASR_MODEL = "openai/whisper-large-v3-turbo"
# No longer a string path for transformers, but a local GGUF file
SAMPLING_RATE = 16000

# ==========================
# LAZY MODEL LOADING
# ==========================
_asr_pipe = None
_llm_instance = None  # <--- Renamed for clarity

def get_asr_pipe():
    global _asr_pipe
    if _asr_pipe is not None:
        return _asr_pipe
    
    device = get_device_for_transformers()
    dtype = get_torch_dtype()
    
    print(f"--- Loading ASR Model: {ASR_MODEL} ---")
    if device == 0:
        print(f"🚀 Using GPU with {dtype}")
    else:
        print(f"💻 Using CPU with {dtype}")
    
    _asr_pipe = pipeline(
        "automatic-speech-recognition",
        model=ASR_MODEL,
        chunk_length_s=30,
        device=device,
        torch_dtype=dtype,
    )
    return _asr_pipe

def get_llm_instance():
    """Loads the CPU-optimized GGUF model."""
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    print(f"--- Loading Local LLM: Sailor2-8B-IQ2_M (GGUF) ---")
    # This automatically downloads the file from HF to your cache if not present
    _llm_instance = Llama.from_pretrained(
        repo_id="bartowski/Sailor2-8B-Chat-GGUF",
        filename="Sailor2-8B-Chat-IQ2_M.gguf",
        n_ctx=2048,    # Context window
        n_threads=8,   # Adjust based on your physical CPU cores
        verbose=False  # Keeps the console clean
    )
    return _llm_instance

# ==========================
# UTILITIES
# ==========================

# Whisper hallucinations: Singlish/Manglish particles that get mis-transcribed
# as real English words. Map the hallucinated form back to the particle.
_WHISPER_HALLUCINATIONS = {
    r'\bLily\b':    'leh',
    r'\bla\b':      'lah',
    r'\bLa\b':      'lah',
    r'\bLor\b':     'lor',
    r'\bMar\b':     'mah',
    r'\bWar\b':     'wor',
    r'\bHor\b':     'hor',
    r'\bSia\b':     'sia',
}

# Filler sounds to strip entirely
_RE_FILLERS = re.compile(
    r'\b(hmm+|hm+|uh+|um+|er+|ah+|oh+|eh+)\b[,.]?',
    re.IGNORECASE,
)

# Trailing/leading punctuation cleanup after filler removal
_RE_MULTI_SPACE = re.compile(r'  +')


def _clean_transcript(text: str) -> str:
    """
    Post-process Whisper output:
    1. Restore Singlish/Manglish particles that Whisper hallucinated as English words.
    2. Strip filler sounds (hmm, uh, um, er).
    3. Tidy up leftover whitespace.
    """
    s = text

    # Restore hallucinated particles
    for pattern, replacement in _WHISPER_HALLUCINATIONS.items():
        s = re.sub(pattern, replacement, s)

    # Strip filler sounds
    s = _RE_FILLERS.sub('', s)

    # Tidy whitespace and trailing punctuation
    s = _RE_MULTI_SPACE.sub(' ', s).strip().strip(',').strip()

    if s != text:
        print(f"[transcript] cleaned: '{text}' -> '{s}'")

    return s


def _detect_dialect(text: str) -> str:
    """
    Detect dialect/language using Sailor2 LLM.
    Recognises ASEAN dialects including Manglish and Singlish.
    """
    sys_msg = (
        "You are an ASEAN Linguistic Expert. Detect the dialect(s) from this list: "
        "Manglish, Singlish, Thai-English, Malay, Hokkien, Cantonese, Tagalog, Taglish, "
        "Indonesian, Thai, Lao, Burmese, Sundanese, Vietnamese, Khmer, English.\n"
        "RULE: If multiple dialects are used, combine them with a '+'.\n"
        "Example: 'Sawadika, where is the shop?' -> Thai+English\n"
        "Example: 'Eh where got cheap makan ah?' -> Manglish\n"
        "Output ONLY the dialect name(s). No extra words or parentheses."
    )
    prompt = (
        f"<|im_start|>system\n{sys_msg}<|im_end|>\n"
        f"<|im_start|>user\nText: {text}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    try:
        llm = get_llm_instance()
        output = llm(prompt, max_tokens=20, stop=["<|im_end|>", "\n\n"], temperature=0.1)
        result = output["choices"][0]["text"].strip()
        return result if result else "English"
    except Exception as e:
        print(f"[dialect] Sailor2 failed: {e}")
        return "English"


def llm_process(text, task, country: str = "Malaysia"):
    if not text or len(text) < 2:
        return {"dialect": "N/A", "question": "No input detected", "query": "N/A"}
    
    if task == "dialect":
        return {"dialect": _detect_dialect(text), "question": "N/A", "query": "N/A"}
    elif task == "question":
        sys_msg = (
            "You are an English Translator. Rewrite the input into ONE clear Standard English question.\n"
            "STRICT RULES:\n"
            "- The output MUST be in English ONLY. Do not use Malay, Thai, or any other language.\n"
            "- Remove all slang and particles.\n"
            "- No bolding, no notes, no parentheses.\n"
            "Output ONLY the English question."
        )
    elif task == "query":
        sys_msg = (
            f"You are a Search Expert. The current user location is {country}.\n"
            "Convert the input into professional English keywords.\n"
            "RULES:\n"
            f"1. If the country is not specified, assume the context is {country}.\n"
            "2. Output must be 100 percent English. Translate all dialect words.\n"
            f"Example: 'renew license' -> {country} driving license renewal requirements online\n"
            "Output ONLY the keywords, no asterisk or other symbols."
        )

    prompt = f"<|im_start|>system\n{sys_msg}<|im_end|>\n<|im_start|>user\nText: {text}<|im_end|>\n<|im_start|>assistant\n"
    
    try:
        llm = get_llm_instance()
        output = llm(prompt, max_tokens=100, stop=["<|im_end|>", "\n\n"], temperature=0.1)
        response = output["choices"][0]["text"].strip()
        
        # FIX: If the task is 'question' or 'query', the small model won't output the label
        # So we force the result into the dictionary even if the label is missing
        results = {"dialect": "N/A", "question": "N/A", "query": "N/A"}
        
        if task == "dialect":
            results["dialect"] = response.replace("DIALECT:", "").strip()
        elif task == "question":
            results["question"] = response.replace("QUESTION:", "").strip()
        elif task == "query":
            results["query"] = response.replace("QUERY:", "").strip()
            
        return results
    except Exception as e:
        print(f"⚠️ LLM Error: {e}")
        return {"dialect": "N/A", "question": "N/A", "query": "N/A"}

# ==========================
# PUSH TO TALK SESSION
# ==========================

class PTTSession:
    def __init__(self):
        self.recording = False
        self.audio_data = []
        self.results = {"dialect": None, "question": None, "query": None}

    def callback(self, indata, frames, time, status):
        if self.recording:
            self.audio_data.append(indata.copy())

    def start_recording(self):
        if not self.recording:
            print("\nRecording... (Release SPACE to stop)")
            self.audio_data = []
            self.recording = True

    def stop_recording(self):
        if self.recording:
            self.recording = False
            print("Processing...")
            self.process_audio()

    # ... (inside PTTSession class) ...

    def process_audio(self):
        if not self.audio_data: return
        audio_np = np.concatenate(self.audio_data, axis=0).flatten()

        # 1. TRANSCRIBE
        asr = get_asr_pipe()
        res = asr(audio_np, generate_kwargs={"task": "transcribe", "language": "english", "do_sample": False})
        raw_text = res["text"].strip()
        
        print(f"Raw Transcription: {raw_text}")
        if len(raw_text) < 2: return

        # Clean up Whisper hallucinations and filler sounds
        raw_text = _clean_transcript(raw_text)
        print(f"Cleaned Transcription: {raw_text}")

        # 2. ANALYZE (Three separate focused passes)
        print("Normalizing and Generating Query...")
        
        # We extract the string result from the dictionary returned by llm_process
        self.dialect_data = llm_process(raw_text, "dialect").get("dialect")
        self.question_data = llm_process(raw_text, "question").get("question")
        self.query_data = llm_process(raw_text, "query").get("query")

        # Update the dictionary that run_assistant() actually returns
        self.results = {
            "dialect": self.dialect_data,
            "question": self.question_data,
            "query": self.query_data
        }

# ==========================
# MAIN
# ==========================

def run_assistant():
    # 1. PRELOAD MODELS (These use the global _asr_pipe and _llm_instance)
    # The helper functions get_asr_pipe() and get_llm_instance() 
    # already handle the "if None" check internally.
    get_asr_pipe()
    get_llm_instance()

    session = PTTSession()

    def on_press(key):
        if key == keyboard.Key.space: session.start_recording()

    def on_release(key):
        if key == keyboard.Key.space:
            session.stop_recording()
            return False 
        if key == keyboard.Key.esc: return False

    stream = sd.InputStream(samplerate=SAMPLING_RATE, channels=1, callback=session.callback)

    print("\n--- ASEAN VOICE ASSISTANT READY ---")
    print("Hold [SPACE] to speak | [ESC] to quit")

    with stream:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    return session.results

def create_session():
    get_asr_pipe()
    get_llm_instance()

    session = PTTSession()

    stream = sd.InputStream(
        samplerate=SAMPLING_RATE,
        channels=1,
        callback=session.callback
    )

    return session, stream

# if __name__ == "__main__":
#     try:
#         # Pre-load to ensure models are ready
#         get_asr_pipe()
#         llm = get_llm_instance()

#         final_results = run_assistant()

#         print("\n" + "="*30)
#         print(f"DETECTED: {final_results.get('dialect')}")
#         print(f"ENGLISH : {final_results.get('question')}")
#         print(f"QUERY   : {final_results.get('query')}")
#         print("="*30)

#     except KeyboardInterrupt:
#         print("\nStopping assistant...")
#     finally:
#         # MANUALLY CLOSE THE LLM
#         # This prevents the TypeError you saw in the traceback
#         if _llm_instance is not None:
#             print("Cleaning up models...")
#             _llm_instance.close()
#             _llm_instance = None