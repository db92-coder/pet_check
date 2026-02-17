from fastapi import FastAPI
from datetime import datetime
import random

app = FastAPI(title="Mock Government Service", version="0.1.0")

@app.get("/ping")
def ping():
    return {"status": "ok", "service": "mock-gov", "time": datetime.utcnow().isoformat()}

@app.post("/eligibility/check")
def eligibility_check(payload: dict):
    owner_id = str(payload.get("owner_id", ""))
    choices = ["ELIGIBLE", "INELIGIBLE", "REVIEW_REQUIRED"]
    if owner_id:
        idx = ord(owner_id[-1]) % len(choices)
        decision = choices[idx]
    else:
        decision = random.choice(choices)

    return {
        "decision": decision,
        "reason": "Simulated response for demo purposes",
        "received": payload,
        "issued_at": datetime.utcnow().isoformat()
    }

@app.post("/cases/report")
def report_case(payload: dict):
    return {
        "receipt_id": f"MOCK-REC-{random.randint(100000, 999999)}",
        "status": "RECEIVED",
        "issued_at": datetime.utcnow().isoformat(),
        "received": payload
    }
