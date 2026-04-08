import os
import yt_dlp
import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)
CHUNK_SIZE = 1024 * 64

def get_best_format(formats):
    best = None
    for f in formats:
        has_video = f.get('vcodec') not in ('none', None)
        has_audio = f.get('acodec') not in ('none', None)
        if has_video and has_audio and f.get('ext') == 'mp4':
            if best is None or f.get('height', 0) > best.get('height', 0):
                best = f
    if not best:
        for f in formats:
            has_video = f.get('vcodec') not in ('none', None)
            has_audio = f.get('acodec') not in ('none', None)
            if has_video and has_audio:
                return f
    return best

def extract_info(youtube_url):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        best = get_best_format(info.get('formats', []))
        return info, best

@app.route('/')
def home():
    return '''
    YouTube Stream API
    Endpoints:
    
      /info?url=YOUTUBE_URL — returns title, duration, quality, stream URL as JSON
      /stream?url=YOUTUBE_URL — stream video directly (paste in VLC Network Stream)
    
    Example:
    
      /info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
    
    '''

@app.route('/info')
def info():
    yt_url = request.args.get('url', '').strip()
    if not yt_url:
        return jsonify({"error": "Missing ?url= parameter"}), 400
    try:
        data, best = extract_info(yt_url)
        duration   = data.get('duration', 0)
        stream_url = best['url'] if best else data.get('url', '')
        height     = best.get('height', '?') if best else '?'
        return jsonify({
            "title":      data.get('title', 'Unknown'),
            "duration":   f"{duration // 60}m {duration % 60}s",
            "quality":    f"{height}p",
            "stream_url": stream_url,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stream')
def stream():
    yt_url = request.args.get('url', '').strip()
    if not yt_url:
        return jsonify({"error": "Missing ?url= parameter"}), 400
    try:
        data, best = extract_info(yt_url)
        raw_url    = best['url'] if best else data.get('url')
        title      = data.get('title', 'video')

        req = requests.get(raw_url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer':    'https://www.youtube.com/',
        }, stream=True)

        def generate():
            for chunk in req.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

        return Response(
            generate(),
            content_type=req.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Content-Disposition': f'inline; filename="{title}.mp4"',
                'Transfer-Encoding':   'chunked',
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"\nAPI running at http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, threaded=True)
