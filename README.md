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
- **Framework**: FastAPI (async, high-performance API)
- **Speech-to-Text**: OpenAI Whisper (`openai-whisper`)
- **NLP**: Hugging Face Transformers (`transformers`, `torch`)
- **Sentiment Model**: `tabularisai/multilingual-sentiment-analysis`
- **Server**: Uvicorn (ASGI server)

### Frontend
- **Framework**: React 19
- **Build Tool**: Vite (Rolldown-based for fast builds)
- **Routing**: React Router DOM
- **Styling**: Tailwind CSS
- **PDF Export**: jsPDF + html2canvas

### Tooling
- **Package Manager**: npm
- **Python Environment**: venv
- **Testing**: pytest (backend unit tests)

---

## Project Structure

```
talksense-ai/
├── backend/
│   ├── main.py                    # FastAPI app + /analyze endpoint
│   ├── services/
│   │   ├── speech_to_text.py      # Whisper transcription
│   │   ├── nlp_engine.py          # Sentiment + keyword extraction
│   │   └── context_analyzer.py    # Meeting/Sales intelligence logic
│   ├── utils/
│   │   └── config_loader.py       # Keyword configurations
│   ├── tests/                     # Unit tests
│   └── requirements.txt           # Python dependencies
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

## How It Works

### Step-by-Step Processing Flow

1. **Audio Upload**
   - User uploads audio file (MP3, WAV, M4A, max 50MB)
   - Selects conversation mode: **Meeting** or **Sales**

2. **Speech-to-Text Transcription**
   - Whisper model processes audio file
   - Generates timestamped transcript segments
   - Extracts full text and segment-level timestamps

3. **NLP Enrichment**
   - Semantic merging combines fragmented segments
   - Sentiment analysis runs on each segment (batch inference)
   - Keywords extracted using domain-specific pattern matching
   - Output: Enriched segments with sentiment labels and confidence scores

4. **Context-Aware Analysis**
   - **Meeting Mode**: Detects decisions, action items, ownership, blockers
   - **Sales Mode**: Detects objections, buying signals, commitments, deal risk
   - Quality scoring based on binary signals (not sentiment-driven)
   - Generates executive summary and key insights

5. **Results Display**
   - Structured JSON response sent to frontend
   - Interactive dashboard displays insights
   - Exportable as PDF report

### Mode-Specific Interpretation Example

**Transcript Segment**: *"I'll send the proposal by Friday"*

| Mode    | Interpretation                                      |
|---------|-----------------------------------------------------|
| Meeting | Action Item: "Send proposal" (Owner: Speaker, Deadline: Friday) |
| Sales   | Hard Commitment + Buying Signal + Follow-Up Action |

---

## Setup & Run Instructions

### Prerequisites

- **Python**: 3.8+ (tested on 3.10)
- **Node.js**: 16+ (tested on 18.x)
- **FFmpeg**: Required by Whisper for audio processing
  - Windows: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

### Backend Setup

```bash
# Navigate to project root
cd talksense-ai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Run backend server
uvicorn backend.main:app --reload
```

Backend will run at: `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd talksense-ui

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will run at: `http://localhost:5173`

### Running the Application

1. Start backend: `uvicorn backend.main:app --reload` (from project root)
2. Start frontend: `npm run dev` (from `talksense-ui/`)
3. Open browser: `http://localhost:5173`
4. Upload audio file or try demo data

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
