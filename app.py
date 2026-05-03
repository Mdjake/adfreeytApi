from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
import yt_dlp

app = FastAPI()

# CHANGE THIS TO YOUR SECRET KEY
VALID_API_KEY = "SAIF@ROMEO999"

def extract_url(video_url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]',
        'extractor_args': {'youtube': {'player_client': ['android_vr', 'ios']}},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            return info.get('url')
        except:
            return None

@app.get("/embed")
async def embed_player(
    url: str = Query(..., description="YouTube URL"),
    key: str = Query(..., description="Your API Key")
):
    # 1. Security Check
    if key != VALID_API_KEY:
        return HTMLResponse(content="<h1>403 Forbidden: Invalid API Key</h1>", status_code=403)

    # 2. Extraction
    direct_link = extract_url(url)
    
    if not direct_link:
        raise HTTPException(status_code=500, detail="Could not extract video")

    # 3. Return the Player (HTML)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ad-Free Player</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body, html {{ margin: 0; padding: 0; height: 100%; background: #000; overflow: hidden; }}
            video {{ width: 100%; height: 100%; object-fit: contain; }}
        </style>
    </head>
    <body>
        <video controls autoplay playsinline>
            <source src="{direct_link}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
