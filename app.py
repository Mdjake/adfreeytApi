from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import redis
import json
import re
import random
from functools import wraps

app = Flask(__name__)
CORS(app)

# Fix 1: Limiter init — use init_app pattern (flask-limiter v2+)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
limiter.init_app(app)

# Fix 2: Redis host was a markdown hyperlink — now a plain string
try:
    cache = redis.Redis(host='localhost', port=6379, decode_responses=True)
    cache.ping()
    CACHE_ENABLED = True
except Exception:
    CACHE_ENABLED = False
    print("Redis not available, caching disabled")


# Fix 5: extract_video_id was called but never defined
def extract_video_id(url_or_id):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    return None


def cached_response(ttl=3600):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not CACHE_ENABLED:
                return f(*args, **kwargs)

            cache_key = f"{request.path}:{request.query_string}"
            cached = cache.get(cache_key)
            if cached:
                return jsonify(json.loads(cached))

            response = f(*args, **kwargs)

            # Fix 4: response may be a tuple (data, status_code) — guard before
            # calling .status_code or .get_data() on it
            if isinstance(response, tuple):
                return response

            if response.status_code == 200:
                cache.setex(cache_key, ttl, response.get_data(as_text=True))

            return response
        return decorated_function
    return decorator


@app.route('/api/v1/player', methods=['GET'])
@limiter.limit("100 per minute")
@cached_response(ttl=300)
def get_player_embed():
    video_input = request.args.get('video')

    if not video_input:
        return jsonify({'error': 'Missing video parameter'}), 400

    video_id = extract_video_id(video_input)
    if not video_id:
        return jsonify({'error': 'Invalid YouTube video ID'}), 400

    nocache = random.randint(100000, 999999)

    embed_url = (
        f"https://www.youtube.com/embed/{video_id}"
        f"?autoplay=1"
        f"&controls=1"
        f"&modestbranding=1"
        f"&rel=0"
        f"&showinfo=0"
        f"&iv_load_policy=3"
        f"&cc_load_policy=0"
        f"&disable_polymer=1"
        f"&nocache={nocache}"
    )

    return jsonify({
        'success': True,
        'video_id': video_id,
        'embed_url': embed_url,
        'embed_html': (
            f'<iframe src="{embed_url}" '
            f'allow="accelerometer; autoplay; clipboard-write; '
            f'encrypted-media; gyroscope; picture-in-picture" '
            f'allowfullscreen></iframe>'
        )
    })


# Fix 3: datetime was used but never imported — now imported at the top
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'cache_enabled': CACHE_ENABLED,
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    app.run(debug=True)
