import os
import re
import time
import logging
import requests
import yt_dlp
from flask import Flask, Response, jsonify, request

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CHUNK_SIZE = 1024 * 64  # 64 KB


# ─── Cookies Setup ───────────────────────────────────────────────────────────
def setup_cookies():
    """Write cookies from env var to /tmp/cookies.txt, fixing common formatting issues."""
    content = os.environ.get("COOKIES_CONTENT", "")
    if not content.strip():
        log.warning("⚠️  No COOKIES_CONTENT env var found — requests may be blocked by YouTube")
        return None

    # Fix escaped newlines/tabs that happen when pasting into env vars
    content = content.replace("\\n", "\n").replace("\\t", "\t")

    path = "/tmp/cookies.txt"
    with open(path, "w") as f:
        f.write(content)

    lines = [l for l in content.splitlines() if l.strip()]
    log.info(f"✅ Cookies written to {path} ({len(lines)} lines)")

    if not lines[0].startswith("# Netscape"):
        log.warning("⚠️  Cookie file may not be in Netscape format — check your COOKIES_CONTENT")

    return path


COOKIES_PATH = setup_cookies()


# ─── Core Extractor ──────────────────────────────────────────────────────────
def extract_info(youtube_url: str) -> dict:
    """
    Extract video info using yt-dlp with:
    - tv_embedded player client (bypasses bot detection)
    - cookies (for authenticated requests)
    - residential proxy (optional, set PROXY_URL env var)
    - automatic fallback player clients
    """
    ydl_opts = {
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                # tv_embedded is least restricted, falls back to web
                "player_client": ["tv_embedded", "web", "android"],
                "player_skip": ["webpage"],  # skip webpage fetch = faster + avoids detection
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        # Retry logic
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 15,
    }

    # Attach cookies if available
    if COOKIES_PATH and os.path.exists(COOKIES_PATH):
        ydl_opts["cookiefile"] = COOKIES_PATH
        log.info("🍪 Using cookies file")
    else:
        log.warning("⚠️  No cookies file found — may get bot-detected")

    # Attach proxy if set
    proxy_url = os.environ.get("PROXY_URL")
    if proxy_url:
        ydl_opts["proxy"] = proxy_url
        log.info(f"🔀 Using proxy: {proxy_url[:30]}...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info


# ─── Helpers ─────────────────────────────────────────────────────────────────
def sanitize_filename(name: str) -> str:
    """Remove characters that break Content-Disposition headers."""
    return re.sub(r'[^\w\s\-.]', '', name).strip() or "video"


# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "endpoints": {
            "/info?url=YOUTUBE_URL": "Get video metadata",
            "/stream?url=YOUTUBE_URL": "Stream video (open in VLC or browser)",
            "/health": "Health check",
            "/debug": "Check cookies/config status",
        }
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": int(time.time())})


@app.route("/debug")
def debug():
    """Check that cookies and config are loaded correctly."""
    content = os.environ.get("COOKIES_CONTENT", "")
    file_exists = os.path.exists("/tmp/cookies.txt") if COOKIES_PATH else False
    preview = None

    if file_exists:
        with open("/tmp/cookies.txt", "r") as f:
            lines = f.readlines()
        preview = lines[0].strip() if lines else "empty file"

    return jsonify({
        "cookies_env_set": bool(content.strip()),
        "cookies_env_length": len(content),
        "cookies_file_exists": file_exists,
        "cookies_file_preview": preview,
        "proxy_set": bool(os.environ.get("PROXY_URL")),
        "yt_dlp_version": yt_dlp.version.__version__,
    })


@app.route("/info")
def info():
    yt_url = request.args.get("url", "").strip()
    if not yt_url:
        return jsonify({"error": "Missing ?url= parameter"}), 400

    try:
        data = extract_info(yt_url)
        duration = data.get("duration") or 0
        return jsonify({
            "title": data.get("title", "Unknown"),
            "duration": f"{int(duration) // 60}m {int(duration) % 60}s",
            "quality": data.get("format_note", "best"),
            "ext": data.get("ext", "mp4"),
            "filesize": data.get("filesize") or data.get("filesize_approx"),
            "thumbnail": data.get("thumbnail"),
            "uploader": data.get("uploader"),
        })
    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        log.error(f"yt-dlp error: {err}")
        if "Sign in" in err or "bot" in err:
            return jsonify({
                "error": "YouTube bot detection triggered",
                "reason": "Your server IP is blocked or cookies are expired/missing",
                "fix": "Set PROXY_URL env var or refresh COOKIES_CONTENT",
            }), 403
        return jsonify({"error": err}), 500
    except Exception as e:
        log.exception("Unexpected error in /info")
        return jsonify({"error": str(e)}), 500


@app.route("/stream")
def stream():
    yt_url = request.args.get("url", "").strip()
    if not yt_url:
        return jsonify({"error": "Missing ?url= parameter"}), 400

    try:
        data = extract_info(yt_url)
        raw_url = data.get("url")

        if not raw_url:
            return jsonify({"error": "Could not extract stream URL — video may be live or geo-blocked"}), 500

        title = sanitize_filename(data.get("title", "video"))
        ext = data.get("ext", "mp4")
        content_type = f"video/{ext}" if ext in ("mp4", "webm") else "video/mp4"

        log.info(f"🎬 Streaming: {title} [{ext}]")

        upstream = requests.get(
            raw_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.youtube.com/",
            },
            stream=True,
            timeout=15,
        )
        upstream.raise_for_status()

        def generate():
            try:
                for chunk in upstream.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()
                log.info(f"🔒 Stream closed: {title}")

        headers = {
            "Content-Disposition": f'inline; filename="{title}.{ext}"',
        }

        # Pass content-length through if available (enables seeking in VLC)
        if "Content-Length" in upstream.headers:
            headers["Content-Length"] = upstream.headers["Content-Length"]
        if "Content-Range" in upstream.headers:
            headers["Content-Range"] = upstream.headers["Content-Range"]

        return Response(
            generate(),
            status=upstream.status_code,
            content_type=upstream.headers.get("Content-Type", content_type),
            headers=headers,
        )

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        log.error(f"yt-dlp error: {err}")
        if "Sign in" in err or "bot" in err:
            return jsonify({
                "error": "YouTube bot detection triggered",
                "fix": "Set PROXY_URL env var or refresh COOKIES_CONTENT",
            }), 403
        return jsonify({"error": err}), 500
    except requests.exceptions.Timeout:
        return jsonify({"error": "Upstream request timed out"}), 504
    except Exception as e:
        log.exception("Unexpected error in /stream")
        return jsonify({"error": str(e)}), 500


# ─── Entry Point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    log.info(f"\n🚀 API running at http://localhost:{port}\n")
    # Use threaded=True for dev only — use gunicorn in production
    app.run(host="0.0.0.0", port=port, threaded=True)
