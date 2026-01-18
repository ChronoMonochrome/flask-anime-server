import os
import mimetypes
from urllib.parse import quote, unquote
from flask import Flask, send_from_directory, render_template_string, abort, Response, Blueprint

app = Flask(__name__)
BASE_DIR = os.path.join("/app/anime_library")
BASE_PATH = "/侍の道"

anisub_bp = Blueprint('anisub', __name__, url_prefix=BASE_PATH)

# --- GLOBAL STYLES ---
KODI_STYLE = """
<style>
    :root { --bg: #0f0f0f; --card-bg: #1a1a1a; --text: #efefef; --accent: #00d1b2; --sub-panel: #242424; }
    body { background-color: var(--bg); color: var(--text); font-family: 'Inter', 'Segoe UI', sans-serif; margin: 0; padding: 0; }
    .content-padding { padding: 20px; }
    h1, h2 { font-weight: 300; color: var(--accent); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px; padding: 20px 0; }
    .card { background: var(--card-bg); border-radius: 12px; overflow: hidden; transition: 0.3s; text-decoration: none; color: inherit; box-shadow: 0 10px 15px rgba(0,0,0,0.5); border: 1px solid #333; }
    .card:hover { transform: translateY(-5px); border-color: var(--accent); }
    .poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .title { padding: 15px; font-size: 0.95em; text-align: center; }
    .back-btn { display: inline-block; margin: 15px; color: var(--accent); text-decoration: none; font-weight: bold; font-size: 0.9em; }
    .episode-list { list-style: none; padding: 0; }
    .episode-list li { margin: 8px 0; background: var(--card-bg); border-radius: 6px; border: 1px solid transparent; }
    .episode-list a { display: block; padding: 15px; color: var(--text); text-decoration: none; }
    .episode-list li.last-played { border-color: var(--accent); background: #252525; }
    .episode-list li.last-played::after { content: ' • LAST WATCHED'; font-size: 0.7em; color: var(--accent); margin-left: 10px; font-weight: bold; }
</style>
"""

def get_poster(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    img_exts = ('.jpg', '.jpeg', '.png', '.webp')
    for ext in img_exts:
        if os.path.exists(os.path.join(folder_path, f'poster{ext}')):
            return f'{BASE_PATH}/poster_file/{quote(folder_name)}/poster{ext}'
    return "https://via.placeholder.com/300x450?text=No+Poster"

@anisub_bp.route('/')
def index():
    folders = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
    html = f"""
    <!DOCTYPE html><html><head><title>Anime Library</title>{KODI_STYLE}</head>
    <body class="content-padding">
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
    <body class="content-padding">
        <a href="{BASE_PATH}/" class="back-btn">← BACK TO LIBRARY</a>
        <h2>{{{{ folder_name }}}}</h2>
        <ul class="episode-list" id="epList">
            {{% for ep in episodes %}}
            <li data-epname="{{{{ ep }}}}">
                <a href="{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ ep | urlencode }}}}">{{{{ ep }}}}</a>
            </li>
            {{% endfor %}}
        </ul>
        <script>
            const history = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
            const lastEp = history["{{{{ folder_name }}}}"]?.last_ep;
            if (lastEp) {{
                document.querySelectorAll('#epList li').forEach(li => {{
                    if (li.getAttribute('data-epname') === lastEp) li.classList.add('last-played');
                }});
            }}
        </script>
    </body></html>
    """
    return render_template_string(template, folder_name=folder_name, episodes=episodes)

@anisub_bp.route('/play/<path:folder_name>/<path:video_name>')
def player(folder_name, video_name):
    folder_name, video_name = unquote(folder_name), unquote(video_name)
    folder_path = os.path.join(BASE_DIR, folder_name)
    video_exts = ('.mkv', '.mp4', '.webm')
    all_eps = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(video_exts)])
    curr_idx = all_eps.index(video_name)
    
    prev_ep = all_eps[curr_idx - 1] if curr_idx > 0 else None
    next_ep = all_eps[curr_idx + 1] if curr_idx < len(all_eps) - 1 else None
    srt_name = os.path.splitext(video_name)[0] + ".srt"

    player_styles = """
    <style>
        #mainPlayerContainer { 
            background: #000; display: flex; flex-direction: column; 
            width: 100%; height: auto; margin: auto; position: relative;
            user-select: none; -webkit-user-select: none;
        }
        .player-wrapper { 
            position: relative; width: 100%; background: #000; 
            touch-action: none; overflow: hidden;
        }
        video { width: 100%; display: block; z-index: 1; }

        #customSubs {
            position: absolute; bottom: 2%; left: 0; width: 100%;
            text-align: center; pointer-events: none; z-index: 10;
            padding: 0 5%; box-sizing: border-box;
        }
        .sub-inner {
            display: inline-block;
            background: rgba(255, 255, 255, 0);
            color: #ffffff;
            font-size: 3.4em;
            padding: 2px 10px;
            border-radius: 4px;
            text-shadow: 2px 2px 2px #000;
            line-height: 1.3;
        }

        .interaction-layer { 
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            z-index: 20; background: transparent;
        }

        .custom-controls {
            position: absolute; bottom: 0; left: 0; width: 100%; height: 85px;
            background: linear-gradient(transparent, rgba(0, 0, 0, 0.9) 70%);
            display: flex; align-items: center; gap: 15px; padding: 0 20px 5px 20px;
            z-index: 100; box-sizing: border-box;
            transition: opacity 0.3s ease;
            opacity: 0; pointer-events: none;
        }
        .custom-controls.visible { opacity: 1; pointer-events: auto; }

        .seek-bar { flex-grow: 1; cursor: pointer; accent-color: var(--accent); }
        .time-display { font-size: 0.85em; color: #eee; min-width: 90px; font-family: monospace; }
        .control-btn { background: none; border: none; color: white; cursor: pointer; padding: 10px; display: flex; align-items: center; }
        .control-btn svg { width: 34px; height: 34px; fill: currentColor; }
        .control-btn:disabled { opacity: 0.2; cursor: default; }

        .subtitle-display { background: #111; padding: 20px; border-top: 1px solid #333; color: white; min-height: 80px; }
        
        #mainPlayerContainer:fullscreen { width: 100vw; height: 100vh; }
        #mainPlayerContainer:fullscreen .player-wrapper { height: 100%; display: flex; align-items: center; }
        #mainPlayerContainer:fullscreen .subtitle-display { display: none; }
        #mainPlayerContainer:fullscreen #customSubs { bottom: 2%; }
    </style>
    """

    template = f"""
    <!DOCTYPE html><html><head><title>{{{{ video_name }}}}</title>{KODI_STYLE}{player_styles}</head>
    <body oncontextmenu="return false;">
        <a href="{BASE_PATH}/show/{{{{ folder_name | urlencode }}}}" class="back-btn">← BACK TO LISTING</a>
        <div id="mainPlayerContainer">
            <div class="player-wrapper" id="videoWrapper">
                <video id="videoPlayer" playsinline>
                    <source src="{BASE_PATH}/stream/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}" type="video/mp4">
                    <track id="mainSub" kind="subtitles" src="{BASE_PATH}/sub/{{{{ folder_name | urlencode }}}}/{{{{ srt_name | urlencode }}}}" default>
                </video>

                <div id="customSubs"><span class="sub-inner" id="subSpan"></span></div>
                <div class="interaction-layer" id="interactLayer"></div>
                
                <div class="custom-controls" id="controlsBar">
                    <button class="control-btn" onclick="location.href='{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ prev_ep | urlencode }}}}'" { 'disabled' if not prev_ep else '' }>
                        <svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
                    </button>

                    <button class="control-btn" onclick="togglePlay()">
                        <svg viewBox="0 0 24 24" id="playIcon"><path d="M8 5v14l11-7z"/></svg>
                    </button>

                    <button class="control-btn" onclick="location.href='{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ next_ep | urlencode }}}}'" { 'disabled' if not next_ep else '' }>
                        <svg viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
                    </button>

                    <input type="range" class="seek-bar" id="seekBar" value="0" step="0.1">
                    <span class="time-display" id="timeDisplay">0:00/0:00</span>
                    
                    <button class="control-btn" onclick="toggleFullScreen()">
                        <svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
                    </button>
                </div>
            </div>

            <div class="subtitle-display">
                <div class="sub-label" style="color:var(--accent); font-size:0.75em; font-weight:bold;">LAST PHRASE</div>
                <div id="subText" style="font-size: 1.2em; margin-top:5px;">...</div>
            </div>
        </div>

        <script>
            const video = document.getElementById('videoPlayer');
            const container = document.getElementById('mainPlayerContainer');
            const interact = document.getElementById('interactLayer');
            const controlsBar = document.getElementById('controlsBar');
            const subSpan = document.getElementById('subSpan');
            const subText = document.getElementById('subText');
            const playIcon = document.getElementById('playIcon');
            const seekBar = document.getElementById('seekBar');
            const timeDisplay = document.getElementById('timeDisplay');
            
            const folder = "{{{{ folder_name }}}}";
            const videoName = "{{{{ video_name }}}}";
            let uiTimer;
            let lastTap = 0;

            // --- PERSISTENCE ---
            video.addEventListener('loadedmetadata', () => {{
                const history = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
                if (history[folder] && history[folder].last_ep === videoName) {{
                    video.currentTime = history[folder].time || 0;
                }}
            }});

            video.addEventListener('timeupdate', () => {{
                if (Math.floor(video.currentTime) % 5 === 0) {{
                    const history = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
                    history[folder] = {{ last_ep: videoName, time: video.currentTime }};
                    localStorage.setItem('anisub_history', JSON.stringify(history));
                }}
                seekBar.value = (video.currentTime / video.duration) * 100 || 0;
                timeDisplay.innerText = formatTime(video.currentTime) + "/" + formatTime(video.duration || 0);
            }});

            // --- UI LOGIC ---
            function showUI() {{
                controlsBar.classList.add('visible');
                document.body.style.cursor = 'default';
                clearTimeout(uiTimer);
                if (!video.paused) {{
                    uiTimer = setTimeout(() => {{
                        controlsBar.classList.remove('visible');
                        document.body.style.cursor = 'none';
                    }}, 2500);
                }}
            }}

            ['mousemove', 'mousedown', 'touchstart', 'pointerdown'].forEach(e => {{
                interact.addEventListener(e, showUI);
            }});

            function togglePlay() {{
                if (video.paused) {{
                    video.play();
                    playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
                }} else {{
                    video.pause();
                    playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
                }}
                showUI();
            }}

            function toggleFullScreen() {{
                if (!document.fullscreenElement) container.requestFullscreen();
                else document.exitFullscreen();
                showUI();
            }}

            interact.addEventListener('pointerdown', (e) => {{
                const rect = interact.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const now = Date.now();
                if (!controlsBar.classList.contains('visible')) {{ showUI(); return; }}
                if (now - lastTap < 300) {{
                    if (x < rect.width/3) video.currentTime -= 10;
                    else if (x > (rect.width/3)*2) video.currentTime += 10;
                    showUI();
                }} else {{
                    if (x > rect.width/3 && x < (rect.width/3)*2) togglePlay();
                }}
                lastTap = now;
            }});

            const track = video.textTracks[0];
            track.mode = 'hidden';
            track.oncuechange = function() {{
                if (this.activeCues && this.activeCues.length > 0) {{
                    const txt = this.activeCues[0].text;
                    subSpan.innerText = txt;
                    subText.innerText = txt;
                }}
            }};

            seekBar.oninput = () => {{ video.currentTime = (seekBar.value / 100) * video.duration; showUI(); }};
            function formatTime(s) {{
                const m = Math.floor(s / 60);
                const rs = Math.floor(s % 60);
                return m + ":" + (rs < 10 ? '0' : '') + rs;
            }}
        </script>
    </body></html>
    """
    return render_template_string(template, folder_name=folder_name, video_name=video_name, srt_name=srt_name, prev_ep=prev_ep, next_ep=next_ep)

# --- REMAINING ROUTES UNCHANGED ---
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

app.register_blueprint(anisub_bp)

@app.route('/')
def root_404():
    abort(404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
