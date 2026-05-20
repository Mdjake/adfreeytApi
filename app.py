from fastapi import FastAPI, HTTPException
import httpx
from pydantic import BaseModel
from typing import Dict, Any
import os

app = FastAPI(title="Telegram ID to Number Proxy API")

# ========== ADDED: API Key System ==========
PROX_API_KEY = os.getenv('TELEGRAM_PROXY_API_KEY', 'TELEGRAM-PROXY-KEY-2024')
# ===========================================

class ResponseModel(BaseModel):
    success: bool
    user_id: str
    country: str
    country_code: str
    number: str
    developer: str

@app.get("/api", response_model=ResponseModel)
async def get_user_number(userid: str, api_key: str):  # CHANGED: Added api_key parameter
    # ========== ADDED: API Key Validation ==========
    if api_key != PROXY_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    # ==============================================
    
    target_url = "https://wasifali-telegram-id-to-number.vercel.app/api"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(target_url, params={"userid": userid})
            response.raise_for_status()
            data = response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Proxy request failed: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    # Validate required fields exist
    required_fields = ["success", "user_id", "country", "country_code", "number"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=502, detail=f"Missing field from upstream API: {field}")
    
    # Construct new response (keep first 5 fields, replace developer)
    filtered_data = {
        "success": data["success"],
        "user_id": data["user_id"],
        "country": data["country"],
        "country_code": data["country_code"],
        "number": data["number"],
        "developer": "@i_amAnanya"   # Your custom value
    }
    
    return filtered_data

# Optional: Root endpoint for health check
@app.get("/")
async def root():
    return {"message": "Telegram ID to Number Proxy API is running", "usage": "/api?userid=<telegram_user_id>"}
