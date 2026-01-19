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
    :root { --bg: #0f0f0f; --card-bg: #1a1a1a; --text: #efefef; --accent: #00d1b2; }
    body { background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
    .content-padding { padding: 20px; }
    h1, h2 { font-weight: 300; color: var(--accent); }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px; padding: 20px 0; }
    .card { background: var(--card-bg); border-radius: 12px; overflow: hidden; transition: 0.3s; text-decoration: none; color: inherit; box-shadow: 0 10px 15px rgba(0,0,0,0.5); border: 1px solid #333; }
    .card:hover { transform: translateY(-5px); border-color: var(--accent); }
    .poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .title { padding: 15px; font-size: 0.95em; text-align: center; }
    .back-btn { display: inline-block; margin: 10px 15px; color: var(--accent); text-decoration: none; font-weight: bold; font-size: 0.9em; z-index: 1000; position: relative; }
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

# --- ROUTES ---

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
            width: 100%; max-height: 92vh; margin: auto; position: relative;
        }
        .player-wrapper { 
            position: relative; width: 100%; background: #000; 
            overflow: hidden; cursor: default; display: flex; align-items: center; justify-content: center;
        }
        video { width: 100%; max-height: 75vh; display: block; z-index: 1; pointer-events: none; }
        .seek-feedback {
            position: absolute; top: 50%; transform: translateY(-50%);
            background: rgba(255,255,255,0.2); border-radius: 50%;
            width: 80px; height: 80px; display: flex; align-items: center; justify-content: center;
            opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 40; color: white; font-weight: bold;
        }
        .seek-left { left: 10%; } .seek-right { right: 10%; }
        .custom-controls {
            position: absolute; bottom: 0; left: 0; width: 100%;
            background: linear-gradient(transparent, rgba(0, 0, 0, 0.95) 70%);
            display: flex; flex-direction: column; padding: 15px; 
            z-index: 100; box-sizing: border-box; transition: opacity 0.4s ease;
            opacity: 1;
        }
        .controls-row { display: flex; align-items: center; justify-content: space-between; margin-top: 5px;}
        .control-group { display: flex; align-items: center; gap: 15px; }
        .control-btn { background: none; border: none; color: white; cursor: pointer; padding: 5px; }
        .control-btn svg { width: 30px; height: 30px; fill: currentColor; }
        .seek-bar { width: 100%; accent-color: var(--accent); cursor: pointer; height: 5px; }
        select { background: #222; color: white; border: 1px solid #444; padding: 4px; border-radius: 4px; }
        .subtitle-display { background: #111; padding: 15px; border-top: 1px solid #333; color: white; min-height: 60px; flex-shrink: 0; }
        #customSubs { position: absolute; bottom: 2%; width: 100%; text-align: center; pointer-events: none; z-index: 10; transition: bottom 0.3s; }
        .sub-inner { color: white; font-size: 2.0em; text-shadow: 2px 2px 4px #000; font-weight: bold; }
        .player-wrapper:fullscreen video { max-height: 100vh; width: 100vw; }
        .hide-cursor { cursor: none !important; }
    </style>
    """

    template = f"""
    <!DOCTYPE html><html><head><title>Anisub Player</title>{KODI_STYLE}{player_styles}</head>
    <body>
        <a href="{BASE_PATH}/show/{{{{ folder_name | urlencode }}}}" class="back-btn">← BACK TO LIST</a>
        <div id="mainPlayerContainer">
            <div class="player-wrapper" id="videoArea" onmousemove="resetTimer()" onclick="handleGlobalClick(event)">
                <video id="videoPlayer" playsinline>
                    <source src="{BASE_PATH}/stream/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}" type="video/mp4">
                    <track id="mainSub" kind="subtitles" src="{BASE_PATH}/sub/{{{{ folder_name | urlencode }}}}/{{{{ srt_name | urlencode }}}}" default>
                </video>
                <div id="seekL" class="seek-feedback seek-left">-10s</div>
                <div id="seekR" class="seek-feedback seek-right">+10s</div>
                <div id="customSubs"><span class="sub-inner" id="subSpan"></span></div>
                <div class="custom-controls" id="controlsBar" onclick="event.stopPropagation()">
                    <input type="range" class="seek-bar" id="seekBar" value="0" step="0.1" oninput="manualSeek(this.value)">
                    <div class="controls-row">
                        <div class="control-group">
                            <button class="control-btn" onclick="location.href='{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ prev_ep | urlencode }}}}'" {{ 'disabled' if not prev_ep else '' }}><svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg></button>
                            <button class="control-btn" onclick="togglePlay()"><svg viewBox="0 0 24 24" id="playIcon"><path d="M8 5v14l11-7z"/></svg></button>
                            <button class="control-btn" onclick="location.href='{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ next_ep | urlencode }}}}'" {{ 'disabled' if not next_ep else '' }}><svg viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg></button>
                        </div>
                        <div class="control-group">
                            <select id="speedSelect" onchange="video.playbackRate = this.value">
                                <option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="1.5">1.5x</option><option value="2">2x</option>
                            </select>
                            <button class="control-btn" onclick="toggleCC()"><svg viewBox="0 0 24 24"><path d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-8 7H9.5V10h-2v4h2v-1H11v1c0 .55-.45 1-1 1H7c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1zm7 0h-1.5V10h-2v4h2v-1H18v1c0 .55-.45 1-1 1h-3c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1z"/></svg></button>
                            <button class="control-btn" onclick="toggleFullScreen()"><svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg></button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="subtitle-display">
                <div style="color:var(--accent); font-size:0.75em; font-weight:bold;">LAST PHRASE</div>
                <div id="subText" style="margin-top:5px;">...</div>
            </div>
        </div>
        <script>
            const video = document.getElementById('videoPlayer');
            const videoArea = document.getElementById('videoArea');
            const controlsBar = document.getElementById('controlsBar');
            const playIcon = document.getElementById('playIcon');
            const seekBar = document.getElementById('seekBar');
            const subSpan = document.getElementById('subSpan');
            const subText = document.getElementById('subText');
            const subContainer = document.getElementById('customSubs');
            
            let uiTimer, lastClick = 0;

            function handleGlobalClick(e) {{
                const now = Date.now();
                const rect = videoArea.getBoundingClientRect();
                const x = e.clientX - rect.left;
                if (now - lastClick < 300) {{
                    if (x < rect.width / 3) triggerSeek('L');
                    else if (x > (rect.width / 3) * 2) triggerSeek('R');
                    lastClick = 0;
                }} else {{
                    togglePlay();
                    lastClick = now;
                }}
                resetTimer();
            }}

            // --- KEYBOARD SHORTCUTS ---
            document.addEventListener('keydown', (e) => {{
                // Ignore if user is typing in a search box or select menu
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

                switch (e.key) {{
                    case 'ArrowLeft':
                        e.preventDefault();
                        video.currentTime = Math.max(0, video.currentTime - 3);
                        triggerSeek('L', '-3s'); // Show feedback with custom text
                        break;
                    case 'ArrowRight':
                        e.preventDefault();
                        video.currentTime = Math.min(video.duration, video.currentTime + 3);
                        triggerSeek('R', '+3s'); // Show feedback with custom text
                        break;
                    case ' ': // Spacebar for play/pause
                        e.preventDefault();
                        togglePlay();
                        break;
                    case 'f': // 'f' for fullscreen
                        e.preventDefault();
                        toggleFullScreen();
                        break;
                }}
                resetTimer(); // Show UI when a key is pressed
            }});

            function togglePlay() {{
                if (video.paused) {{
                    video.play();
                    playIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
                }} else {{
                    video.pause();
                    playIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
                }}
            }}

            function triggerSeek(dir, label) {{
                const el = document.getElementById(dir === 'L' ? 'seekL' : 'seekR');

                // If no label passed (from the click handler), default to 10s
                if (!label) {{
                    video.currentTime += (dir === 'L' ? -10 : 10);
                    el.innerText = dir === 'L' ? '-10s' : '+10s';
                }} else {{
                    el.innerText = label;
                }}

                el.style.opacity = '1';
                setTimeout(() => {{ el.style.opacity = '0'; }}, 500);
            }}

            function resetTimer() {{
                controlsBar.style.opacity = '1';
                controlsBar.style.pointerEvents = 'auto';
                videoArea.classList.remove('hide-cursor');
                subContainer.style.bottom = "15%";
                clearTimeout(uiTimer);
                if (!video.paused) {{
                    uiTimer = setTimeout(() => {{
                        controlsBar.style.opacity = '0';
                        controlsBar.style.pointerEvents = 'none';
                        videoArea.classList.add('hide-cursor');
                        subContainer.style.bottom = "2%";
                    }}, 3000);
                }}
            }}

            function toggleCC() {{
                const track = video.textTracks[0];
                if (track.mode === 'hidden' || track.mode === 'showing') {{
                    track.mode = 'disabled';
                    subSpan.innerText = "";
                }} else {{
                    track.mode = 'hidden';
                }}
                resetTimer();
            }}

            function toggleFullScreen() {{
                if (!document.fullscreenElement) videoArea.requestFullscreen();
                else document.exitFullscreen();
            }}

            function manualSeek(val) {{
                video.currentTime = (val / 100) * video.duration;
            }}

            video.addEventListener('timeupdate', () => {{
                seekBar.value = (video.currentTime / video.duration) * 100 || 0;
                if (Math.floor(video.currentTime) % 5 === 0) {{
                    const history = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
                    history["{folder_name}"] = {{ last_ep: "{video_name}", time: video.currentTime }};
                    localStorage.setItem('anisub_history', JSON.stringify(history));
                }}
            }});

            const track = video.textTracks[0];
            track.mode = 'hidden';
            track.oncuechange = function() {{
                if (this.mode !== 'disabled' && this.activeCues?.length > 0) {{
                    const txt = this.activeCues[0].text;
                    subSpan.innerText = subText.innerText = txt;
                }} else if (this.activeCues?.length === 0) {{
                    subSpan.innerText = "";
                }}
            }};

            video.addEventListener('loadedmetadata', () => {{
                const hist = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
                if (hist["{folder_name}"]?.last_ep === "{video_name}") {{
                    video.currentTime = hist["{folder_name}"]?.time || 0;
                }}
                resetTimer();
            }});
            
            video.addEventListener('pause', resetTimer);
            video.addEventListener('play', resetTimer);
        </script>
    </body></html>
    """
    return render_template_string(template, folder_name=folder_name, video_name=video_name, srt_name=srt_name, prev_ep=prev_ep, next_ep=next_ep)

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
