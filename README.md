# TalkSense AI

**Offline-First Conversation Intelligence Platform for Meetings and Sales Calls**

---

## Overview

TalkSense AI is an **offline-first conversation intelligence platform** that analyzes meeting recordings and sales calls to extract actionable insights. Unlike cloud-based solutions that rely on proprietary LLMs, TalkSense AI uses **pretrained open-source models** (Whisper for transcription, multilingual sentiment analysis) combined with a **rule-based context intelligence layer** to deliver explainable, transparent insights.

### Problem Statement

Teams and sales professionals struggle to extract actionable insights from recorded conversations. Existing solutions either:
- Require expensive cloud subscriptions with opaque AI processing
- Lack explainability (black-box LLM summaries)
- Don't differentiate between meeting contexts (internal discussions vs. client calls)

TalkSense AI addresses this by providing **mode-aware analysis** that interprets the same transcript differently based on conversation type, while maintaining full transparency in how insights are generated.

### Value Proposition

- **Offline-First**: No cloud dependencies, no API costs, complete data privacy
- **Explainable AI**: Rule-based intelligence layer shows exactly how insights are derived
- **Context-Aware**: Same transcript analyzed differently for Meeting vs. Sales modes
- **Fast**: Analysis completes in under 60 seconds for most recordings
- **Transparent**: No black-box LLM summarization—every insight is traceable

---

## Key Features

### Meeting Intelligence

Designed for **internal team discussions** and **project meetings**:

- **Executive Summary**: Quality assessment based on decision-making and ownership signals
- **Meeting Quality Score**: Evaluates execution clarity (High/Medium/Low)
- **Decisions Detected**: Extracts directional commitments and locked-in decisions
- **Action Items**: Identifies tasks with ownership and timeline extraction
- **Tension Points**: Flags unresolved blockers, risks, and dependencies
- ## Speaker Attribution Evaluation

A new script `backend/evaluate_speaker_attribution.py` provides a command‑line tool to generate a markdown report for a session. It extracts speaker attribution diagnostics from `session_metrics` and computes speaker distribution and change statistics.

```bash
python -m backend.evaluate_speaker_attribution <session_id>
```

The report includes coverage, speaker counts, and speaker change rate.
- **Sentiment Analysis**: Per-segment sentiment tracking with confidence scores
- **Key Insights**: Highlights critical moments requiring attention

### Sales Call Intelligence

Optimized for **client conversations** and **sales discovery calls**:

- **Executive Summary**: Deal quality assessment based on buyer engagement signals
- **Sales Quality Score**: Evaluates deal momentum (High/Medium/Low)
- **Objections Detected**: Identifies pricing, timing, authority, and feature concerns
- **Objection Handling**: Recommends resolution strategies for each objection type
- **Buying Signals**: Detects budget alignment, decision-maker presence, and value articulation
- **Follow-Up Actions**: Stage-based recommendations (e.g., "Send proposal by Friday")
- **Commitment Tracking**: End-of-call commitment detection with timeline extraction
- **Deal Risk Flags**: Identifies disqualification signals (no intent, deferred decisions)

---

## System Architecture

TalkSense AI follows a **3-stage processing pipeline**:

```
Audio Upload → Speech-to-Text → NLP Enrichment → Context Analysis → Structured Insights
```

### Stage 1: Speech-to-Text (Whisper)
- **Model**: OpenAI Whisper (base model)
- **Output**: Timestamped transcript segments
- **Performance**: Balances speed and accuracy for real-time processing

### Stage 2: NLP Enrichment
- **Sentiment Analysis**: `tabularisai/multilingual-sentiment-analysis` (Hugging Face Transformers)
- **Keyword Extraction**: Rule-based pattern matching for domain-specific terms
- **Semantic Merging**: Combines fragmented segments using linguistic continuity markers
- **Output**: Enriched segments with sentiment labels, confidence scores, and keywords

### Stage 3: Context Intelligence Layer
- **Meeting Mode**: Analyzes for decisions, action items, ownership, and blockers
- **Sales Mode**: Analyzes for objections, buying signals, commitment, and deal risk
- **Quality Scoring**: Binary signal detection (ownership, execution decisions, commitments)
- **Insight Generation**: Rule-based extraction with explainable logic

### Key Design Principle
**Same transcript, different interpretation**: The context analyzer applies mode-specific rules to extract insights tailored to the conversation type. For example, "I'll send the proposal by Friday" is:
- **Meeting Mode**: Action item with owner and deadline
- **Sales Mode**: Hard commitment + buying signal + follow-up action

---

## Tech Stack

### Backend
- **Framework**: FastAPI (async ASGI API)
- **Database**: PostgreSQL (with SQLAlchemy ORM & `asyncpg` driver)
- **Speech-to-Text**: Faster Whisper (`faster-whisper`)
- **Voice Activity Detection**: Silero VAD (`silero-vad`)
- **Speaker Diarization**: Pyannote Speaker Diarization (`pyannote.audio`)
- **NLP Processing**: Hugging Face Transformers (`transformers`, `torch`) for sentiment analysis and keyphrase extraction
- **Server**: Uvicorn (ASGI server)
- **Migrations**: Alembic (`alembic`)

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite
- **Routing**: React Router DOM
- **Styling**: Tailwind CSS
- **Communication**: WebSockets (for real-time streaming audio metrics) and HTTP REST APIs
- **PDF Export**: jsPDF + html2canvas

---

## Project Structure

```
talksense-ai/
├── backend/
│   ├── main.py                    # FastAPI app + WebSocket & HTTP endpoints
│   ├── core/
│   │   └── config.py              # Settings definition (Pydantic Settings)
│   ├── db/
│   │   ├── database.py            # PostgreSQL async connection pool & session
│   │   ├── models.py              # SQLAlchemy ORM models
│   │   └── crud.py                # Database queries and session flushes
│   ├── services/
│   │   ├── speech_to_text.py      # Whisper transcription pipeline
│   │   ├── nlp_engine.py          # Sentiment + keyword extraction
│   │   └── context_analyzer.py    # Meeting/Sales intelligence rules
│   ├── tests/                     # Unit and integration tests
│   ├── requirements.txt           # Production dependencies
│   ├── requirements-dev.txt       # Dev & CI dependencies
│   ├── pyproject.toml             # Dev tools (Black, Ruff, Pyright) configuration
│   └── pytest.ini                 # Pytest configuration
│
├── talksense-ui/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.jsx       # Landing page
│   │   │   ├── UploadPage.jsx     # Audio upload + mode selection
│   │   │   └── ResultsPage.jsx    # Insights dashboard
│   │   ├── services/
│   │   │   └── api.js             # Backend API client
│   │   └── assets/                # Logos, images
│   ├── package.json               # Node dependencies
│   └── vite.config.js             # Vite configuration
│
├── sample_audio/                  # Demo audio files
├── sample_results/                # Pre-generated demo results (JSON)
└── README.md                      # This file
```

---

## System Architecture

TalkSense AI leverages a **3-stage processing pipeline** with real-time feedback mechanisms:

1. **Audio Upload & Streaming (HTTP & WebSockets)**:
   - High-throughput endpoint handles standard audio uploads.
   - WebSockets support live/streaming metric updates and real-time state synchronization.
2. **Audio Processing (VAD, Whisper, Pyannote)**:
   - **Voice Activity Detection**: Silero VAD filters non-speech segments.
   - **Speech-to-Text**: Faster Whisper transcribes speech into text.
   - **Speaker Diarization**: Pyannote Speaker Diarization tags who spoke when.
3. **NLP Processing & Context Analysis**:
   - Sentiment analysis is done at a segment level using pretrained Hugging Face Transformers.
   - Rule-based contextual intelligence categorizes data depending on the selected mode (**Meeting** or **Sales**).
4. **Session Management & Database (PostgreSQL)**:
   - Metadata, transcripts, speaker metrics, and summaries are persisted in PostgreSQL.
   - Alembic manages database versioning and migrations.

---

## Setup & Run Instructions

### Prerequisites

- **Python**: 3.10+
- **Node.js**: 18.x+
- **FFmpeg**: Required by Whisper for audio processing
  - Windows: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

### Environment Variables

Before running the application, you must configure the backend environment variables.

1. Navigate to the backend directory and copy the environment example template:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Open `backend/.env` and fill in the required variables (e.g., your database connection string, Hugging Face Token for speaker diarization, Gemini API Key if using LLM classification features).

### Backend Setup & Run

1. Navigate to the project root and create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - **Windows (PowerShell)**: `venv\Scripts\Activate.ps1`
   - **macOS/Linux**: `source venv/bin/activate`
3. Install production/runtime dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Run Alembic database migrations to set up the PostgreSQL schema:
   ```bash
   cd backend
   alembic upgrade head
   ```
5. Start the FastAPI development server:
   ```bash
   uvicorn backend.main:app --reload
   ```
   The backend will run at: `http://localhost:8000`

### Frontend Setup & Run

1. Navigate to the frontend directory:
   ```bash
   cd talksense-ui
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will run at: `http://localhost:5173`

---

## Development & Testing

For local development, testing, and CI/CD validation, follow the guidelines below.

### Backend Verification

First, install the development dependencies:
```bash
pip install -r backend/requirements-dev.txt
```

**Running Tests**
Run the pytest suite from the `backend/` directory:
```bash
cd backend
pytest
```

**Code Formatting**
Ensure code follows Black style guidelines:
```bash
cd backend
black --check .
```

**Linting**
Run Ruff to check for syntax and stylistic issues:
```bash
cd backend
ruff check .
```

**Type Checking**
Run Pyright to perform static type analysis:
```bash
cd backend
pyright
```

### Frontend Verification

**CI Installation**
Perform a clean installation of node dependencies:
```bash
cd talksense-ui
npm ci
```

**Building for Production**
Verify the production build succeeds:
```bash
cd talksense-ui
npm run build
```

**Linting**
Run ESLint to check for frontend code issues:
```bash
cd talksense-ui
npm run lint
```

---

## Design Decisions & Constraints

### Offline-First Rationale
- **Data Privacy**: No conversation data leaves the local machine
- **Cost Efficiency**: No cloud API costs (OpenAI, Google Cloud, etc.)
- **Transparency**: Users can inspect and modify the intelligence layer
- **Hackathon Scope**: Faster iteration without cloud infrastructure setup

### Pretrained Models (No Custom Training)
- **Whisper**: Industry-standard STT with strong multilingual support
- **Sentiment Model**: Pretrained multilingual model (no domain-specific fine-tuning)
- **Trade-off**: Slightly lower accuracy vs. custom-trained models, but faster deployment

### Rule-Based Intelligence Layer
- **Explainability**: Every insight is traceable to specific rules and patterns
- **No Black-Box AI**: Unlike LLM-based summarization, logic is fully transparent
- **Trade-off**: Requires manual rule curation, but ensures predictable outputs

### Hackathon-Driven Scope
- **MVP Focus**: Core features only (no integrations, no user auth)
- **Demo-Ready**: Pre-generated sample results for quick evaluation
- **Monolithic Architecture**: Single FastAPI app (no microservices complexity)

---

## Limitations

- **Sentiment Model**: Not fine-tuned for business conversations (may misclassify domain-specific language)
- **Speaker Diarization**: Not implemented (cannot distinguish between multiple speakers)
- **Language Support**: Optimized for English (multilingual model supports others, but rules are English-centric)
- **Scalability**: Single-threaded processing (no distributed task queue)
- **Audio Quality**: Performance degrades with poor audio quality or heavy background noise
- **Rule Coverage**: Context intelligence rules are not exhaustive (edge cases may be missed)

---

## Future Improvements

- **Hybrid LLM Integration**: Optional LLM-based summarization for nuanced insights (e.g., GPT-4 for executive summaries)
- **Speaker Diarization**: Identify and label individual speakers in multi-person conversations
- **Fine-Tuned Sentiment**: Domain-specific sentiment model trained on business conversations
- **Real-Time Processing**: WebSocket-based streaming for live transcription
- **Integration APIs**: Slack, Zoom, Google Meet integrations for automatic recording ingestion
- **Custom Rule Builder**: UI for non-technical users to define custom intelligence rules
- **Multi-Language Support**: Expand rule sets for non-English languages

---

## License & Usage

This project was developed as a **hackathon submission** and is intended for **educational and demonstration purposes**. 

- **Not Production-Ready**: This is an MVP built under time constraints
- **No Warranty**: Use at your own risk
- **Open for Learning**: Feel free to explore, fork, and adapt for your own projects

---

## Acknowledgments

- **OpenAI Whisper**: Speech-to-text foundation
- **Hugging Face**: Pretrained sentiment analysis model
- **FastAPI**: High-performance backend framework
- **React + Vite**: Modern frontend stack

---

**Built for SCET Breakout Hackathon 2026**  
*Demonstrating the power of explainable AI in conversation intelligence*
