from fastapi import FastAPI, Query, HTTPException
import httpx

app = FastAPI()

# Original API configuration
ORIGINAL_API_URL = "https://noobster-api-5xii.onrender.com/search"
ORIGINAL_API_KEY = "mr_noobster"

@app.get("/search")
async def search_phone(mobile: str = Query(...)):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                ORIGINAL_API_URL,
                params={"mobile": mobile, "key": ORIGINAL_API_KEY}
            )
            response.raise_for_status()
            original_data = response.json()
        
        # Extract only what we need and rename
        results = original_data.get("results", {}).get("results", {})
        
        return {
            "number": results.get("n"),
            "country": results.get("c"),
            "country_code": results.get("cc"),
            "developer": "@i_AmAnanya"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))