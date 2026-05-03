from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for embedding

# YouTube video ID validation
YOUTUBE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{11}$')
YOUTUBE_URL_PATTERN = re.compile(
    r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&\n?#]+)'
)

def extract_video_id(input_str):
    """Extract YouTube video ID from URL or direct ID"""
    input_str = input_str.strip()
    
    # Check if it's already a video ID
    if YOUTUBE_ID_PATTERN.match(input_str):
        return input_str
    
    # Extract from URL
    match = YOUTUBE_URL_PATTERN.search(input_str)
    if match:
        return match.group(1)
    
    return None

@app.route('/api/v1/player', methods=['GET'])
def get_player_embed():
    """
    Get embeddable player URL for ad-free YouTube video
    
    Query parameters:
    - video: YouTube video ID or URL
    - autoplay: 0 or 1 (default: 1)
    - controls: 0 or 1 (default: 1)
    - modestbranding: 0 or 1 (default: 1)
    - rel: 0 or 1 (default: 0)
    
    Returns: Redirect to embed URL or JSON with embed info
    """
    video_input = request.args.get('video')
    autoplay = request.args.get('autoplay', '1')
    controls = request.args.get('controls', '1')
    modestbranding = request.args.get('modestbranding', '1')
    rel = request.args.get('rel', '0')
    format_type = request.args.get('format', 'redirect')  # 'redirect' or 'json'
    
    if not video_input:
        return jsonify({'error': 'Missing video parameter'}), 400
    
    video_id = extract_video_id(video_input)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube video ID or URL'}), 400
    
    # Build embed URL with ad-blocking parameters
    embed_url = (
        f"https://www.youtube.com/embed/{video_id}"
        f"?autoplay={autoplay}"
        f"&controls={controls}"
        f"&modestbranding={modestbranding}"
        f"&rel={rel}"
        f"&showinfo=0"
        f"&iv_load_policy=3"
        f"&cc_load_policy=0"
        f"&enablejsapi=1"
        f"&origin={request.headers.get('Origin', 'https://skipcut.com')}"
    )
    
    if format_type == 'redirect':
        return redirect(embed_url)
    else:
        return jsonify({
            'success': True,
            'video_id': video_id,
            'embed_url': embed_url,
            'embed_html': f'<iframe width="100%" height="100%" src="{embed_url}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
        })

@app.route('/api/v1/player/direct', methods=['GET'])
def direct_embed_html():
    """Return directly embeddable HTML iframe code"""
    video_input = request.args.get('video')
    
    if not video_input:
        return jsonify({'error': 'Missing video parameter'}), 400
    
    video_id = extract_video_id(video_input)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube video ID or URL'}), 400
    
    embed_url = (
        f"https://www.youtube.com/embed/{video_id}"
        f"?autoplay=1"
        f"&controls=1"
        f"&modestbranding=1"
        f"&rel=0"
        f"&showinfo=0"
        f"&iv_load_policy=3"
        f"&cc_load_policy=0"
        f"&enablejsapi=1"
    )
    
    iframe_html = f'''<iframe 
    width="100%" 
    height="100%" 
    src="{embed_url}" 
    frameborder="0" 
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
    referrerpolicy="strict-origin-when-cross-origin" 
    allowfullscreen>
</iframe>'''
    
    return Response(iframe_html, mimetype='text/html')

@app.route('/api/v1/info', methods=['GET'])
def get_video_info():
    """Get video information without loading the player"""
    video_input = request.args.get('video')
    
    if not video_input:
        return jsonify({'error': 'Missing video parameter'}), 400
    
    video_id = extract_video_id(video_input)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube video ID or URL'}), 400
    
    # Fetch video info from YouTube oEmbed
    import requests
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    
    try:
        response = requests.get(oembed_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'video_id': video_id,
                'title': data.get('title'),
                'author': data.get('author_name'),
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'thumbnail_medium': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            })
        else:
            return jsonify({
                'success': True,
                'video_id': video_id,
                'title': 'YouTube Video',
                'author': 'YouTube',
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'thumbnail_medium': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            })
    except:
        return jsonify({
            'success': True,
            'video_id': video_id,
            'title': 'YouTube Video',
            'author': 'YouTube',
            'thumbnail': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            'thumbnail_medium': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
