from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Mock Vet System", version="0.1.0")

@app.get("/ping")
def ping():
    return {"status": "ok", "service": "mock-vet", "time": datetime.utcnow().isoformat()}

@app.post("/visits/push")
def push_visit(payload: dict):
    return {
        "ack": True,
        "message": "Simulated visit ingestion",
        "received": payload,
        "processed_at": datetime.utcnow().isoformat()
    }
