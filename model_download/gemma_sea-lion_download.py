# Use a pipeline as a high-level helper
from transformers import pipeline

pipe = pipeline("text-generation", model="aisingapore/Llama-SEA-LION-v3-8B-IT")
messages = [
    {"role": "user", "content": "Who are you?"},
]
pipe(messages)