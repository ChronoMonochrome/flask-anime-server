import os
import mimetypes
from urllib.parse import quote, unquote
from flask import Flask, send_from_directory, render_template_string, abort, Response, Blueprint

app = Flask(__name__)
BASE_DIR = os.path.join("/app/anime_library")

# Define the custom base path
BASE_PATH = "/侍の道"

# Create a Blueprint for the scoped routes
anisub_bp = Blueprint('anisub', __name__, url_prefix=BASE_PATH)

# --- KODI & ANISUB INSPIRED CSS (Unchanged styles) ---
KODI_STYLE = """
<style>
    :root { --bg: #0f0f0f; --card-bg: #1a1a1a; --text: #efefef; --accent: #00d1b2; --sub-panel: #242424; }
    body { background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; margin: 0; padding: 20px; }
    h1, h2 { font-weight: 300; color: var(--accent); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px; padding: 20px 0; }
    .card { background: var(--card-bg); border-radius: 12px; overflow: hidden; transition: 0.3s; text-decoration: none; color: inherit; border: 1px solid #333; }
    .card:hover { transform: translateY(-5px); border-color: var(--accent); }
    .poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .title { padding: 15px; font-size: 0.95em; text-align: center; }
    .back-btn { display: inline-block; margin-bottom: 20px; color: var(--accent); text-decoration: none; font-weight: bold; }
    .episode-list { list-style: none; padding: 0; }
    .episode-list li { margin: 8px 0; background: var(--card-bg); border-radius: 6px; }
    .episode-list a { display: block; padding: 15px; color: var(--text); text-decoration: none; }
</style>
"""

# --- HELPERS ---
def get_poster(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    img_exts = ('.jpg', '.jpeg', '.png', '.webp')
    for ext in img_exts:
        if os.path.exists(os.path.join(folder_path, f'poster{ext}')):
            # Updated to include BASE_PATH in the URL
            return f'{BASE_PATH}/poster_file/{quote(folder_name)}/poster{ext}'
    return "https://via.placeholder.com/300x450?text=No+Poster"

# --- SCOPED ROUTES (Inside Blueprint) ---

@anisub_bp.route('/')
def index():
    folders = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
    html = f"""
    <!DOCTYPE html><html><head><title>Anime Library</title>{KODI_STYLE}</head>
    <body>
        <h1>Anime Library</h1>
        <div class="grid">
            {{% for folder in folders %}}
            <a href="{BASE_PATH}/show/{{{{ folder | urlencode }}}}" class="card">
                <img class="poster" src="{{{{ get_poster(folder) }}}}" alt="Poster">
                <div class="title">{{{{ folder }}}}</div>
            </a>
            {{% endfor %}}
        </div>
    </body></html>
    """
    return render_template_string(html, folders=folders, get_poster=get_poster)

@anisub_bp.route('/show/<path:folder_name>')
def list_episodes(folder_name):
    folder_name = unquote(folder_name)
    folder_path = os.path.join(BASE_DIR, folder_name)
    if not os.path.exists(folder_path): abort(404)
    video_exts = ('.mkv', '.mp4', '.webm')
    episodes = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(video_exts)])
    template = f"""
    <!DOCTYPE html><html><head><title>{{{{ folder_name }}}}</title>{KODI_STYLE}</head>
    <body>
        <a href="{BASE_PATH}/" class="back-btn">← BACK TO LIBRARY</a>
        <h2>{{{{ folder_name }}}}</h2>
        <ul class="episode-list">
            {{% for ep in episodes %}}
            <li><a href="{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ ep | urlencode }}}}">{{{{ ep }}}}</a></li>
            {{% endfor %}}
        </ul>
    </body></html>
    """
    return render_template_string(template, folder_name=folder_name, episodes=episodes)

@anisub_bp.route('/play/<path:folder_name>/<path:video_name>')
def player(folder_name, video_name):
    # (Player logic remains same as previous version, just updating back button)
    folder_name, video_name = unquote(folder_name), unquote(video_name)
    srt_name = os.path.splitext(video_name)[0] + ".srt"
    
    # ... [Insert the player CSS/HTML from the previous successful version here] ...
    # Ensure back button uses: <a href="{BASE_PATH}/show/{{{{ folder_name | urlencode }}}}" class="back-btn">
    
    # Note: Ensure the <track> and <source> tags use the BASE_PATH:
    # <source src="{BASE_PATH}/stream/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}" ...>
    # <track src="{BASE_PATH}/sub/{{{{ folder_name | urlencode }}}}/{{{{ srt_name | urlencode }}}}" ...>
    
    return render_template_string(template_from_previous_step, folder_name=folder_name, video_name=video_name, srt_name=srt_name, BASE_PATH=BASE_PATH)

@anisub_bp.route('/stream/<path:folder_name>/<path:video_name>')
def stream_video(folder_name, video_name):
    return send_from_directory(os.path.join(BASE_DIR, unquote(folder_name)), unquote(video_name))

@anisub_bp.route('/poster_file/<path:folder_name>/<path:filename>')
def serve_poster(folder_name, filename):
    return send_from_directory(os.path.join(BASE_DIR, unquote(folder_name)), unquote(filename))

@anisub_bp.route('/sub/<path:folder_name>/<path:srt_name>')
def serve_subs(folder_name, srt_name):
    folder_name, srt_name = unquote(folder_name), unquote(srt_name)
    path = os.path.join(BASE_DIR, folder_name, srt_name)
    if not os.path.exists(path): return abort(404)
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        srt_content = f.read()
    vtt_content = "WEBVTT\n\n" + srt_content.replace(',', '.')
    return Response(vtt_content, mimetype='text/vtt')

# Register the Blueprint
app.register_blueprint(anisub_bp)

# --- GLOBAL ROUTES ---
@app.route('/')
def root_404():
    abort(404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
