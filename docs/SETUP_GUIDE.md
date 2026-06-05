# TalkSense AI — Developer Environment Setup Guide

> **For:** New contributors setting up TalkSense AI for the first time  
> **OS:** Windows 10 / 11  
> **Last updated:** June 2026

---

## What You're Setting Up

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| AI / ML | faster-whisper, Pyannote, Transformers |
| GPU Acceleration | PyTorch with CUDA 12.4 |
| Database | PostgreSQL 17 |
| Frontend | React 19, Vite, Tailwind CSS |
| Runtime | Node.js 20+ |

---

## Step 0 — Prerequisites

Install these before anything else. Download links provided.

### 0.1 — Python 3.12

Download: https://www.python.org/downloads/release/python-3128/

- Pick **Windows installer (64-bit)**
- ✅ Check **"Add Python to PATH"** during install
- Verify:
  ```powershell
  python --version
  # Expected: Python 3.12.x
  ```

---

### 0.2 — Node.js 20 LTS

Download: https://nodejs.org/en/download

- Pick **Windows (x64) LTS**
- Verify:
  ```powershell
  node --version   # Expected: v20.x.x
  npm --version    # Expected: 10.x.x
  ```

---

### 0.3 — Git

Download: https://git-scm.com/download/win

- Use default options during install
- Verify:
  ```powershell
  git --version
  ```

---

### 0.4 — PostgreSQL 17

Download: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

- Pick **PostgreSQL 17, Windows x86-64**
- During install:
  - Set a password for the `postgres` superuser — **write it down**
  - Keep the default port: `5432`
  - Keep the default locale
- After install, verify PostgreSQL is running:
  ```powershell
  pg_isready
  # Expected: :5432 - accepting connections
  ```

---

### 0.5 — NVIDIA GPU Drivers + CUDA Toolkit

> ⚠️ **Required only if your PC has an NVIDIA GPU (RTX / GTX series).**  
> If you have no NVIDIA GPU, skip this section — the project will run on CPU (slower but functional).

**Check your GPU:**
```powershell
nvidia-smi
```
If this command works, you have an NVIDIA GPU. Note the **CUDA Version** shown in the top-right of the output.

**Install CUDA Toolkit 12.4:**  
Download: https://developer.nvidia.com/cuda-12-4-0-download-archive

- Select: Windows → x86_64 → 10/11 → exe (local)
- Run the installer, use Express installation
- Verify:
  ```powershell
  nvcc --version
  # Expected: Cuda compilation tools, release 12.x
  ```

---

## Step 1 — Get the Code

```powershell
git clone https://github.com/<your-org>/talksense-ai.git
cd talksense-ai
```

> Replace `<your-org>` with the actual GitHub org/username. Ask the project owner for access if needed.

---

## Step 2 — Backend Setup

### 2.1 — Create a Virtual Environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

Your terminal prompt should now show `(venv)` at the start.

> **Always activate the venv before running any backend commands.**  
> To deactivate later: `deactivate`

---

### 2.2 — Install PyTorch (CUDA or CPU)

This step is different depending on whether you have an NVIDIA GPU.

#### Option A — NVIDIA GPU (Recommended)

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

#### Option B — CPU Only (No NVIDIA GPU)

```powershell
pip install torch torchaudio
```

**Verify PyTorch install:**
```powershell
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

Expected output (GPU):
```
PyTorch: 2.x.x+cu124
CUDA: True
```

Expected output (CPU):
```
PyTorch: 2.x.x+cpu
CUDA: False
```

---

### 2.3 — Install Python Dependencies

```powershell
pip install -r requirements.txt
```

> ⏳ This will take several minutes. `faster-whisper`, `pyannote`, and `transformers` are large downloads.

---

### 2.4 — Set Up Environment Variables

Copy the example env file:
```powershell
copy .env.example .env
```

Open `.env` and fill in the required values:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:<your_postgres_password>@localhost:5432/talksense

# JWT Auth
JWT_SECRET_KEY=<generate a random 32-char string>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Hugging Face (for Pyannote speaker diarization)
HF_TOKEN=<your huggingface token>

# App
ENV=development
```

**Generate a JWT secret key:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and paste it as `JWT_SECRET_KEY`.

**Get your Hugging Face token:**
1. Go to https://huggingface.co/settings/tokens
2. Create a new token with **Read** access
3. Paste it as `HF_TOKEN`

> ⚠️ You also need to **accept the Pyannote model license** on HuggingFace:  
> https://huggingface.co/pyannote/speaker-diarization-3.1  
> Click "Agree and access repository". This is a one-time step per HF account.

---

### 2.5 — Set Up the Database

**Create the TalkSense database:**
```powershell
psql -U postgres -c "CREATE DATABASE talksense;"
psql -U postgres -c "CREATE USER talksense_user WITH PASSWORD 'yourpassword';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE talksense TO talksense_user;"
```

> If you use `talksense_user` instead of `postgres`, update your `DATABASE_URL` in `.env` accordingly.

**Run database migrations** (creates all tables):
```powershell
python -m alembic upgrade head
```

---

### 2.6 — Verify the Backend

```powershell
uvicorn main:app --reload --port 8000
```

Open your browser: http://localhost:8000/health

Expected response:
```json
{"status": "TalkSense AI backend running"}
```

Open the interactive API docs: http://localhost:8000/docs

---

## Step 3 — Frontend Setup

Open a **new terminal** (keep the backend terminal running).

```powershell
cd talksense-ui
npm install
```

Start the dev server:
```powershell
npm run dev
```

Open your browser: http://localhost:5173

---

## Step 4 — Verify GPU Acceleration

Run this script to confirm AI models can use your GPU:

```powershell
cd backend
python -c "
import torch
from faster_whisper import WhisperModel

print('=== GPU Check ===')
print(f'CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')

print()
print('=== Whisper Model Load ===')
device = 'cuda' if torch.cuda.is_available() else 'cpu'
compute = 'int8' if torch.cuda.is_available() else 'int8'
model = WhisperModel('small', device=device, compute_type=compute)
print(f'Whisper loaded on: {device}')
print('All good!')
"
```

Expected output (GPU):
```
=== GPU Check ===
CUDA Available: True
GPU: NVIDIA GeForce RTX xxxx
VRAM: x.x GB

=== Whisper Model Load ===
Whisper loaded on: cuda
All good!
```

---

## Step 5 — Full Stack Verification Checklist

Before you start development, confirm all of these work:

- [ ] `python --version` → 3.12.x
- [ ] `node --version` → v20.x.x
- [ ] `pg_isready` → accepting connections on :5432
- [ ] `(venv)` appears in your terminal when backend is active
- [ ] `torch.cuda.is_available()` → True (if you have NVIDIA GPU)
- [ ] Whisper model loads without errors
- [ ] http://localhost:8000/health returns `{"status": "TalkSense AI backend running"}`
- [ ] http://localhost:5173 loads the TalkSense UI

---

## Common Issues & Fixes

### `torch.cuda.is_available()` returns False despite having an NVIDIA GPU

**Cause:** CPU-only PyTorch is installed.  
**Fix:** Reinstall PyTorch with the CUDA wheel:
```powershell
pip uninstall torch torchaudio -y
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

---

### `pg_isready` fails or PostgreSQL won't connect

**Check if PostgreSQL service is running:**
```powershell
Get-Service -Name postgresql*
```
If it shows `Stopped`:
```powershell
Start-Service -Name postgresql-x64-17
```

---

### `pip install -r requirements.txt` fails on `pyannote.audio`

**Cause:** Pyannote requires `torch` to already be installed.  
**Fix:** Always install PyTorch **first** (Step 2.2) before running `requirements.txt`.

---

### `HF_TOKEN` not working / Pyannote 403 error

1. Confirm you've accepted the model license at:  
   https://huggingface.co/pyannote/speaker-diarization-3.1
2. Confirm your token has **Read** permissions on HuggingFace
3. Confirm `.env` is in the `backend/` folder, not the root

---

### Frontend shows blank page or CORS error

**Check that backend is running** on port 8000.  
**Check `.env.example`** in `talksense-ui/` — copy it to `.env.local` and set:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

### Out of VRAM error during inference

Your GPU may have less than 4GB VRAM.  
**Fix:** In `backend/.env`, set:
```env
WHISPER_MODEL=small
WHISPER_COMPUTE_TYPE=int8
PYANNOTE_ENABLED=false
```
This switches to the smaller Whisper model and disables Pyannote diarization.

---

## Project Structure Reference

```
talksense-ai/
├── backend/                  ← Python FastAPI backend
│   ├── main.py               ← App entry point
│   ├── requirements.txt      ← Python dependencies
│   ├── .env                  ← Your local secrets (not in git)
│   ├── .env.example          ← Template (committed to git)
│   ├── audio/                ← VAD, buffer, transcription
│   ├── engine/               ← Conversation engine, alert engine
│   ├── ws/                   ← WebSocket handlers
│   ├── db/                   ← SQLAlchemy models, migrations
│   ├── services/             ← NLP, analysis, memory
│   └── utils/                ← Config loader, helpers
│
├── talksense-ui/             ← React frontend (Vite)
│   ├── src/
│   │   ├── pages/            ← Route-level pages
│   │   ├── components/       ← Reusable UI components
│   │   ├── hooks/            ← Custom React hooks (WebSocket, audio)
│   │   └── services/         ← API client
│   └── package.json
│
├── docs/
│   ├── SETUP_GUIDE.md        ← This file
│   └── archive/              ← Architecture docs
│
└── scripts/                  ← Utility scripts
```

---

## Running the Project Day-to-Day

**Terminal 1 — Backend:**
```powershell
cd talksense-ai/backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd talksense-ai/talksense-ui
npm run dev
```

Then open: http://localhost:5173

---

## Need Help?

- Check `error_log.txt` in the project root for backend errors
- API docs are always at http://localhost:8000/docs when backend is running
- Backend logs appear in the terminal where you ran `uvicorn`
