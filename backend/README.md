# TalkSense AI - Backend

**Offline-First Conversation Intelligence Platform**

This is the backend for **TalkSense AI**, a privacy-focused conversation analysis tool. It processes audio meetings and sales calls entirely offline using local AI models (Whisper & Transformers) to generate structured insights like sentiment trends, action items, and objection detection.

---

## 🏗 Architecture & Logic Flow

The backend follows a **Unidirectional Data Flow** pipeline optimized for responsiveness using FastAPI and Thread Pools.

```mermaid
graph TD
    A[Client Upload] -->|POST /analyze| B(FastAPI Endpoint)
    B -->|Thread Pool| C{Processing Pipeline}
    
    subgraph "Core Logic (Non-Blocking)"
        C -->|1. Transcribe| D[Whisper (STT)]
        D -->|Raw Segments| E[NLP Engine]
        E -->|2. Enrich| F[HuggingFace Transformers]
        F -->|Sentiment + Keywords| G{Analysis Mode}
        
        G -->|Meeting Mode| H[Context Analyzer: Meeting]
        G -->|Sales Mode| I[Context Analyzer: Sales]
        
        H -->|Rule Mapping| J[Decisions & Actions]
        I -->|Rule Mapping| K[Objections & Signals]
    end
    
    J --> L[JSON Response]
    K --> L
```

### 1. Speech-to-Text (STT)
- **Engine**: OpenAI Whisper (`base` model).
- **Function**: Converts audio to text segments with timestamps.
- **Optimization**: Loaded once at startup; runs in a thread pool to avoid blocking the API main loop.

### 2. NLP Enrichment
- **Engine**: `tabularisai/multilingual-sentiment-analysis` (DistilBERT).
- **Function**: Enriches each text segment with:
  - **Sentiment Score**: (-1.0 to 1.0) and Label (Positive/Negative/Neutral).
  - **Confidence**: Model certainty score.
  - **Keywords**: Fast regex-based extraction (decisions, dates, etc.).

### 3. Context Analysis (Rule-Based)
After enrichment, data is passed to specialized analyzers based on the selected `mode`:

- **Meeting Mode** (`analyze_meeting`):
  - **Summary**: Heuristic generation based on sentiment ratio and end-call tone.
  - **Action Items**: Detects phrases like "I will", "to do".
  - **Decisions**: Detects consensus phrases like "agreed", "decided".

- **Sales Mode** (`analyze_sales`):
  - **Overall Sentiment**: Classifies call as Positive, Negative, Neutral, or Mixed.
  - **Objections**: Classifies concerns into *Pricing, Timeline, Authority, Fit*.
  - **Recommended Actions**: Generates follow-ups based on detected objections.

---

## ⚙️ Configuration & Concurrency

### Configurable Keywords (`config/keywords.json`)
Detection logic, such as words triggering an "Objection" or "Decision", is **not hardcoded**. 
You can tune these rules in `backend/config/keywords.json` without restarting the server.
- **Benefits**: Allows on-the-fly tuning for demos or specific industry jargon.

### Concurrency Strategy
- **Problem**: Whisper and Transformers are CPU-heavy and blocking.
- **Solution**: We use `starlette.concurrency.run_in_threadpool`.
- **Effect**: The API remains responsive (e.g., `/health` checks pass instantly) even while a large file is being transcribed on a background thread.

---

## 🚀 Setup & Usage

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run Server
```bash
uvicorn main:app --reload
```
*Server runs on `http://localhost:8000`*

### 3. API Endpoints

#### `POST /analyze`
Uploads an audio file for processing.
- **Params**: 
  - `file`: Audio file (mp3, wav, m4a)
  - `mode`: `"meeting"` or `"sales"` (default: meeting)
- **Response**:
```json
{
  "mode": "sales",
  "transcript": [...],
  "insights": {
    "objections": [...],
    "buying_signals": [...],
    "recommended_actions": [...]
  }
}
```

#### `GET /health`
Returns quick status check (useful for load balancers).
```json
{ "status": "TalkSense AI backend running" }
```
