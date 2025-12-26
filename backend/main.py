from fastapi import FastAPI

app = FastAPI(
    title="TalkSense AI",
    description="AI Conversation Intelligence Platform",
    version="1.0"
)

@app.get("/health")
def health_check():
    return {"status": "TalkSense AI backend running"}
