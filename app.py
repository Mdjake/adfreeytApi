from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI()

def extract_video_data(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]',
        'extractor_args': {
            'youtube': {
                'player_client': ['android_vr', 'ios'],
                'skip': ['webpage']
            }
        },
        # Vercel environments sometimes need this for compatibility
        'nocheckcertificate': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            return {
                "status": "success",
                "title": info.get('title'),
                "url": info.get('url'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration')
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.get("/api/extract")
async def extract(url: str = Query(..., description="The YouTube video URL")):
    result = extract_video_data(url)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.get("/")
async def root():
    return {"message": "Saif's Video Extraction API is Live!"}
