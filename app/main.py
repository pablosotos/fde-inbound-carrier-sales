from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os

from .models import Load
from .load_service import search_loads
from .call_log_service import append_call_log, read_all_logs

load_dotenv()

API_KEY = os.getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

app = FastAPI(title="Inbound Carrier Loads API")

async def get_api_key(api_key: str = Depends(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )


class CallLog(BaseModel):
    carrier_name: Optional[str] = None
    mc_number: Optional[str] = None
    load_id: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    loadboard_rate: Optional[str] = None
    agreed_rate: Optional[str] = None
    counter_offers: Optional[str] = None   
    neg_rounds: Optional[str] = None
    deal_reached: Optional[str] = "false"
    call_outcome: Optional[str] = None   
    carrier_sentiment: Optional[str] = None  


@app.get("/health")
def health():
    print("✅ Health check OK")
    return {"status": "ok"}


@app.get("/loads", response_model=List[Load])
def get_loads(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    equipment_type: Optional[str] = None,
    api_key: str = Depends(get_api_key),
):
    return search_loads(origin=origin, destination=destination, equipment_type=equipment_type)


@app.post("/log-call", status_code=201)
def log_call(
    payload: CallLog,
    api_key: str = Depends(get_api_key),
):
    append_call_log(payload.model_dump())
    print(f"📋 Call logged | carrier={payload.carrier_name} | outcome={payload.call_outcome}")
    return {"status": "logged"}


@app.get("/call-logs")
def get_call_logs(api_key: str = Depends(get_api_key)):
    return read_all_logs()
 