import os
import yt_dlp
import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)
CHUNK_SIZE = 1024 * 64

# write cookies from env to temp file
cookies_content = os.environ.get('COOKIES_CONTENT')
if cookies_content:
    with open('/tmp/cookies.txt', 'w') as f:
        f.write(cookies_content)
    COOKIES_PATH = '/tmp/cookies.txt'
else:
    COOKIES_PATH = None


def extract_info(youtube_url):
    ydl_opts = {
        'format': 'best',  # <- FIXED (no overengineering)
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    if COOKIES_PATH:
        ydl_opts['cookiefile'] = COOKIES_PATH

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info


@app.route('/')
def home():
    return '''
    YouTube Stream API

    /info?url=YOUTUBE_URL   -> get video info
    /stream?url=YOUTUBE_URL -> stream video (use VLC)

    '''


@app.route('/info')
def info():
    yt_url = request.args.get('url', '').strip()
    if not yt_url:
        return jsonify({"error": "Missing ?url= parameter"}), 400

    try:
        data = extract_info(yt_url)

        duration = data.get('duration', 0)
        return jsonify({
            "title": data.get('title', 'Unknown'),
            "duration": f"{duration // 60}m {duration % 60}s",
            "quality": data.get('format_note', 'best'),
            "stream_url": data.get('url'),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stream')
def stream():
    yt_url = request.args.get('url', '').strip()
    if not yt_url:
        return jsonify({"error": "Missing ?url= parameter"}), 400

    try:
        data = extract_info(yt_url)
        raw_url = data.get('url')
        title = data.get('title', 'video')

        req = requests.get(
            raw_url,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://www.youtube.com/',
            },
            stream=True
        )

        def generate():
            for chunk in req.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

        return Response(
            generate(),
            content_type=req.headers.get('Content-Type', 'video/mp4'),
            headers={
                'Content-Disposition': f'inline; filename="{title}.mp4"',
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"\nAPI running at http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, threaded=True)
