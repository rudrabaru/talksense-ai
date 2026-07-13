FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required for soundfile/audio processing
RUN apt-get update && apt-get install -y libsndfile1 ffmpeg libportaudio2 && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first
RUN pip install --no-cache-dir torch==2.3.1 torchaudio==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY diart_inference.py .

ENTRYPOINT ["python", "diart_inference.py"]
