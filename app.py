from fastapi import FastAPI, Query, HTTPException
import httpx
from typing import Optional, Dict, Any

app = FastAPI(title="Phone Info API", description="Custom API wrapper for phone number lookup")

# Original API configuration
ORIGINAL_API_URL = "https://noobster-api-5xii.onrender.com/search"
ORIGINAL_API_KEY = "mr_noobster"

@app.get("/search")
async def search_phone(
    mobile: str = Query(..., description="Phone number to lookup", example="8002008433")
):
    """
    Fetch phone number information from original API and return renamed fields.
    Removes req_left, req_total, expiry. Adds developer @i_AmAnanya.
    """
    try:
        # Call the original API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                ORIGINAL_API_URL,
                params={"mobile": mobile, "key": ORIGINAL_API_KEY}
            )
            response.raise_for_status()
            original_data = response.json()
        
        # Transform the response
        transformed_data = transform_response(original_data)
        return transformed_data
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Original API error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Failed to reach original API: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

def transform_response(original: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform original API response according to requirements:
    - Keep only 'results' and 'developer' fields
    - Rename 'cc' -> 'country_code', 'n' -> 'number' inside results.results (if present in your expected format)
    - Actually, original API returns different structure, so I'll handle both
    """
    # Based on the actual API response I see
    if "data" in original and "channel" in original:
        # This is the format from the actual API you shared
        transformed = {
            "status": original.get("status"),
            "channel": original.get("channel"),
            "data": original.get("data"),  # Keep the user data array
            "developer": "@i_AmAnanya"  # Replace original developer
        }
        return transformed
    
    # Fallback for the example format you wrote (if API changes)
    elif "results" in original:
        inner_results = original.get("results", {}).get("results", {})
        renamed_results = {}
        
        if "n" in inner_results:
            renamed_results["number"] = inner_results["n"]
        if "cc" in inner_results:
            renamed_results["country_code"] = inner_results["cc"]
        if "c" in inner_results:
            renamed_results["country"] = inner_results["c"]
        
        return {
            "results": renamed_results,
            "developer": "@i_AmAnanya"
        }
    
    else:
        # If structure is unknown, return as-is but add your developer name
        original["developer"] = "@i_AmAnanya"
        return original

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "Welcome to tg num API",
        "endpoint": "/search?mobile=tg_id",
        "developer": "@i_AmAnanya"
        
    }