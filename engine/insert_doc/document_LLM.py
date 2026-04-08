import json
import asyncio
import ollama
from engine.speech.text_to_speech import speak_answer

USER_LANGUAGE = "en"
TTS_COUNTRY_CODE = "MY"
ENABLE_TTS = True

class InclusiveCitizenAI:
    def __init__(self, schema_path, user_language="Bahasa Melayu"):
        with open(schema_path, 'r') as f:
            self.fields = json.load(f)
        
        self.responses = {}
        self.current_field_index = 0
        self.user_language = user_language
        # Use a fast local model. 'llama3.2' or 'gemma2:2b' are great for this.
        self.model_id = 'llama3.2' 

    def set_language(self, new_language):
        self.user_language = new_language

    def generate_question(self):
        if self.current_field_index >= len(self.fields):
            return None
        
        field = self.fields[self.current_field_index]
        
        # Skip headers automatically
        if field.get('type') == 'section_header':
            self.current_field_index += 1
            return self.generate_question()
            
        label = field.get('label') or field.get('original_label') or "this field"
        
        # NEW HARDENED PROMPT
        prompt = f"""
        [INST]
        You are a friendly assistant for 'The Inclusive Citizen'.
        TECHNICAL LABEL: "{label}"
        LANGUAGE: {self.user_language}

        TASK:
        1. Remove technical codes like 'A1', 'B2', or '(A1)'.
        2. Remove instructions in parentheses like '(seperti di MyKad)'.
        3. Translate into a natural, friendly question in {self.user_language}.

        EXAMPLES:
        Label: "Nama (seperti di MyKad) A1" -> "What is your full name?"
        Label: "Nombor MyKad A2" -> "Please tell me your IC number."

        Return ONLY the question. No quotes.
        [/INST]
        """
        
        response = ollama.chat(model=self.model_id, messages=[
            {'role': 'user', 'content': prompt},
        ])
        question_text = response['message']['content'].strip().replace('"', '')

        if ENABLE_TTS:
            print(f"[TTS] Speaking: {question_text}") # Debug log
            asyncio.run(speak_answer(question_text, TTS_COUNTRY_CODE))

        return question_text

    def extract_and_save(self, user_audio_text):
        field = self.fields[self.current_field_index]
        label = field.get('label') or field.get('original_label')

        # FEW-SHOT PROMPT: Giving the model examples of what we want
        prompt = f"""
        You are a data extraction tool.
        
        EXAMPLES:
        User: "My name is John Doe" | Field: "Name" | Output: John Doe
        User: "I live in Penang" | Field: "Address" | Output: Penang
        User: "I don't know" | Field: "IC Number" | Output: RETRY
        User: "My phone is 0123456" | Field: "Phone" | Output: 0123456

        ACTUAL TASK:
        User Speech: "{user_audio_text}"
        Target Field: "{label}"
        
        Output ONLY the extracted value. No sentences. If not found, output RETRY.
        Output:"""

        response = ollama.chat(model=self.model_id, messages=[
            {'role': 'user', 'content': prompt},
        ])
        
        # Clean the output
        value = response['message']['content'].strip().split('\n')[0] # Take only the first line
        value = value.replace('Output:', '').replace('"', '').strip()

        # Final check
        if "RETRY" in value.upper() or len(value) < 2:
            print(f"DEBUG: Model returned '{value}', which triggered a RETRY.")
            return "RETRY"

        self.responses[label] = value
        self.current_field_index += 1
        return value

    def get_final_json(self):
        return json.dumps(self.responses, indent=2)

if __name__ == "__main__":
    schema_path = "JSON_storage/lhdn_mystr_2026_updated.json"

    print("--- Starting The Inclusive Citizen (LOCAL OLLAMA) ---")
    assistant = InclusiveCitizenAI(schema_path, user_language="English")

    # 1. Test Question Generation
    print("\n[AI is generating the first question...]")
    question = assistant.generate_question()
    print(f"Assistant says: \"{question}\"")

    # 2. Test Data Extraction
    user_input = "My name is Chook Yao Yu"
    print(f"\n[User speaks: \"{user_input}\"]")
    
    extracted_value = assistant.extract_and_save(user_input)
    print(f"System Recorded: {extracted_value}")

    # 3. Show Final Progress
    print("\n--- Current Form Progress ---")
    print(assistant.get_final_json())