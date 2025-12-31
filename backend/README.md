# TalkSense AI - Backend

The backend for TalkSense AI is a **FastAPI** application that provides offline speech analysis capabilities. It orchestrates the flow from audio transcription to NLP enrichment and context-aware insight generation.

## 🚀 Features

- **Offline Speech-to-Text**: Powered by OpenAI's `whisper` model.
- **NLP Enrichment**: Uses Hugging Face `transformers` for local sentiment analysis and keyword extraction.
- **Context Awareness**: specialized logic for analyzing **Meetings** (action items, decisions) vs. **Sales Calls** (objections, buying signals).
- **No Cloud APIs**: Runs entirely on your local machine for privacy and zero latency during demos.

## 🛠️ Setup & Installation

1. **Prerequisites**: Python 3.10+ installed.

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: This will download PyTorch and Transformers, which may take a few minutes.*

## 🏃‍♂️ Running the Server

Start the API server using Uvicorn:

```bash
uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000`.

### API Documentation
Once running, visit **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** for the interactive Swagger UI.

## 🔌 API Endpoints

### `POST /analyze`
Uploads an audio file and returns structured intelligence.

**Parameters:**
- `file`: Audio file (`.mp3`, `.wav`)
- `mode`: Analysis context (`"meeting"` or `"sales"`)

**Response Example:**
```json
{
  "filename": "meeting.mp3",
  "mode": "meeting",
  "transcript": { ... },
  "insights": {
    "action_items": ["Send report"],
    "meeting_quality": "good",
    "sentiment_score": 0.8
  }
}
```

## 📂 Project Structure

```text
backend/
├── main.py                 # FastAPI application entry point & API routes
├── requirements.txt        # Python dependencies
├── verify_session.py       # Script for session validation
├── services/               # Core intelligence modules
│   ├── speech_to_text.py   # Wrapper for Whisper ASR
│   ├── nlp_engine.py       # Sentiment analysis & keyword extraction
│   ├── context_analyzer.py # Logic for specific modes (Sales vs Meeting)
│   ├── pattern_miner.py    # Advanced pattern detection (risks, trends)
│   ├── insight_composer.py # Generates human-readable summaries
│   ├── timeline_builder.py # Constructs chronological events
│   ├── prediction/         # ML models for outcome prediction
│   └── embeddings/         # Vector embeddings logic
├── uploads/                # Temporary storage for uploaded audio files
└── tests/                  # Unit and integration tests
```

## 🔧 Core Services Overview

| Service | Responsibility |
| :--- | :--- |
| **speech_to_text** | Converts raw audio bytes into text with timestamps. |
| **nlp_engine** | Enriches text with sentiment scores (-1 to 1) and keywords. |
| **context_analyzer** | Applies business logic to interpret NLP data based on the selected mode. |
| **pattern_miner** | Identifies complex sequences (e.g., "Objection followed by Discount"). |
