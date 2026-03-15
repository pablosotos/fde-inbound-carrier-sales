from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from typing import List, Optional
from dotenv import load_dotenv
import os

from .models import Load
from .load_service import search_loads

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

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/loads", response_model=List[Load])
def get_loads(
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    equipment_type: Optional[str] = None,
    api_key: str = Depends(get_api_key),
):
    return search_loads(origin=origin, destination=destination, equipment_type=equipment_type)
