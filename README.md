## Voice Q&A (STT → Web → Answer → TTS)

This folder follows the flow implemented in `main.py`:

1. Push-to-talk recording (hold/release **SPACE**)
2. Speech-to-text transcription
3. Dialect detection + normalization into:
   - a **clear question** (`question`)
   - a **web search query** (`query`)
4. Web search + summarization
5. Clean the summary into a direct answer (Sailor2)
6. Speak the answer (offline Windows TTS)

## What runs

- **Entry point**: `main.py`
- **Speech to text**: `speech_to_text.py` (ASR via `transformers`)
- **Web + summarization**: `web_scraping.py` (DuckDuckGo + trafilatura + Ollama)
- **Answer cleaning + TTS**: `text_to_speech.py` (Sailor2 + `pyttsx3`)

## Setup (Windows / PowerShell)

Create venv + install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Download the spaCy model (required by `web_scraping.py`):

```powershell
.\.venv\Scripts\python -m spacy download en_core_web_sm
```

## Ollama requirement

`web_scraping.py` calls Ollama at `http://localhost:11434/api/generate` using model `llama3.2`.

```powershell
ollama pull llama3.2
```

## Run

```powershell
.\.venv\Scripts\python main.py
```

Controls:

- Hold **SPACE** to record
- Release **SPACE** to process

`main.py` prints:

- `raw`: raw transcription
- `dialect`: detected dialect (heuristic-based)
- `question`: normalized question
- `query`: normalized search query (sent to web scraping)
- `summary`: result from `web_scraping.search_web(query)`
- `cleaned answer`: Sailor2-cleaned answer spoken by TTS

## Notes / troubleshooting

- **First run is slow**: models download the first time (`transformers` + `torch`).
- **Sailor2 can be slow on CPU**: if it fails, TTS falls back to speaking the summary.
- **Voices vary by Windows install**: `pyttsx3` picks the closest available voice based on detected dialect.

## Voice Q&A (STT → Web → Answer → TTS)

This project follows the flow implemented in `main.py`:

1. Push-to-talk recording (hold/release **SPACE**)
2. Speech-to-text transcription
3. Dialect detection + normalization into:
   - a **clear question** (`question`)
   - a **web search query** (`query`)
4. Web search + summarization
5. Clean the summary into a direct answer (Sailor2)
6. Speak the answer (offline Windows TTS)

## What runs

- **Entry point**: `main.py`
- **Speech to text**: `speech_to_text.py` (ASR via `transformers`)
- **Web + summarization**: `web_scraping.py` (DuckDuckGo + trafilatura + Ollama)
- **Answer cleaning + TTS**: `text_to_speech.py` (Sailor2 + `pyttsx3`)

## Setup (Windows / PowerShell)

Create venv + install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Download the spaCy model (required by `web_scraping.py`):

```powershell
.\.venv\Scripts\python -m spacy download en_core_web_sm
```

## Ollama requirement

`web_scraping.py` calls Ollama at `http://localhost:11434/api/generate` using model `llama3.2`.

```powershell
ollama pull llama3.2
```

## Run

```powershell
.\.venv\Scripts\python main.py
```

Controls:

- Hold **SPACE** to record
- Release **SPACE** to process

`main.py` prints:

- `raw`: raw transcription
- `dialect`: detected dialect (heuristic-based)
- `question`: normalized question
- `query`: normalized search query (sent to web scraping)
- `summary`: result from `web_scraping.search_web(query)`
- `cleaned answer`: Sailor2-cleaned answer spoken by TTS

## Notes / troubleshooting

- **First run is slow**: models download the first time (`transformers` + `torch`).
- **Sailor2 can be slow on CPU**: if it fails, TTS falls back to speaking the summary.
- **Voices vary by Windows install**: `pyttsx3` picks the closest available voice based on detected dialect.

