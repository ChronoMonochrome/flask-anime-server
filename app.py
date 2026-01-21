import os
import cv2
import mimetypes
from urllib.parse import quote, unquote
from flask import Flask, send_from_directory, render_template_string, abort, Response, Blueprint, request, send_file

app = Flask(__name__)
BASE_DIR = os.path.join("/app/anime_library")
BASE_PATH = "/侍の道"

# Blueprint for the anime sub-application
anisub_bp = Blueprint('anisub', __name__, url_prefix=BASE_PATH)

preview_caps = {}

# --- GLOBAL STYLES ---
KODI_STYLE = """
<style>
    :root { --bg: #0f0f0f; --card-bg: #1a1a1a; --text: #efefef; --accent: #00d1b2; --mobile-gap: 12px; }
    body { background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; margin: 0; padding: 0; overflow-x: hidden; -webkit-tap-highlight-color: transparent; }
    h1, h2 { font-weight: 300; color: var(--accent); margin-left: 10px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; padding: 15px; }

    @media (min-width: 768px) {
        .grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 25px; }
    }

    .card { background: var(--card-bg); border-radius: 12px; overflow: hidden; transition: 0.3s; text-decoration: none; color: inherit; box-shadow: 0 10px 15px rgba(0,0,0,0.5); border: 1px solid #333; }
    .card:hover { transform: translateY(-5px); border-color: var(--accent); }
    .poster { width: 100%; aspect-ratio: 2/3; object-fit: cover; }
    .title { padding: 10px; font-size: 0.85em; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .back-btn { display: inline-block; margin: 10px 15px; color: var(--accent); text-decoration: none; font-weight: bold; font-size: 0.9em; z-index: 1000; position: relative; }
    .episode-list { list-style: none; padding: 15px; margin: 0; }
    .episode-list li { margin: 8px 0; background: var(--card-bg); border-radius: 8px; border: 1px solid transparent; }
    .episode-list a { display: block; padding: 18px; color: var(--text); text-decoration: none; font-size: 0.95em; }
    .episode-list li.last-played { border-color: var(--accent); background: #252525; }
</style>
"""

def get_poster(folder_name):
    folder_path = os.path.join(BASE_DIR, folder_name)
    img_exts = ('.jpg', '.jpeg', '.png', '.webp')
    for ext in img_exts:
        if os.path.exists(os.path.join(folder_path, f'poster{ext}')):
            return f'{BASE_PATH}/poster_file/{quote(folder_name)}/poster{ext}'
    return "https://via.placeholder.com/300x450?text=No+Poster"

@anisub_bp.route('/preview/<path:folder_name>/<path:video_name>')
def get_preview(folder_name, video_name):
    try:
        t = float(request.args.get('t', 0))
        video_path = os.path.join(BASE_DIR, unquote(folder_name), unquote(video_name))
        if video_path not in preview_caps:
            if len(preview_caps) > 5:
                old_path = next(iter(preview_caps))
                preview_caps[old_path].release()
                del preview_caps[old_path]
            preview_caps[video_path] = cv2.VideoCapture(video_path)
        cap = preview_caps[video_path]
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        success, frame = cap.read()
        if not success: return abort(404)
        height, width = frame.shape[:2]
        new_width = 180
        new_height = int(height * (new_width / width))
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return Response(buffer.tobytes(), mimetype='image/jpeg')
    except Exception: abort(500)

@anisub_bp.route('/')
def index():
    folders = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
    return render_template_string(f"""
    <!DOCTYPE html><html><head><title>Anime Library</title><meta name="viewport" content="width=device-width, initial-scale=1.0">{KODI_STYLE}</head>
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
    """, folders=folders, get_poster=get_poster)

@anisub_bp.route('/show/<path:folder_name>')
def list_episodes(folder_name):
    folder_name = unquote(folder_name)
    folder_path = os.path.join(BASE_DIR, folder_name)
    if not os.path.exists(folder_path): abort(404)
    video_exts = ('.mkv', '.mp4', '.webm')
    episodes = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(video_exts)])
    return render_template_string(f"""
    <!DOCTYPE html><html><head><title>{{{{ folder_name }}}}</title><meta name="viewport" content="width=device-width, initial-scale=1.0">{KODI_STYLE}</head>
    <body>
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
    """, folder_name=folder_name, episodes=episodes)

@anisub_bp.route('/play/<path:folder_name>/<path:video_name>')
def player(folder_name, video_name):
    folder_name, video_name = unquote(folder_name), unquote(video_name)
    folder_path = os.path.join(BASE_DIR, folder_name)

    possible_res = ['240p', '360p', '480p', '720p', '1080p']
    available_res = [r for r in possible_res if os.path.isdir(os.path.join(folder_path, r))]

    video_exts = ('.mkv', '.mp4', '.webm')
    all_eps = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(video_exts)])

    try:
        curr_idx = all_eps.index(video_name)
    except ValueError:
        abort(404)

    prev_ep = all_eps[curr_idx - 1] if curr_idx > 0 else None
    next_ep = all_eps[curr_idx + 1] if curr_idx < len(all_eps) - 1 else None
    srt_name = os.path.splitext(video_name)[0] + ".srt"

    player_styles = """
    <style>
        #mainPlayerContainer { background: #000; display: flex; flex-direction: column; width: 100%; height: 100vh; height: 100svh; position: fixed; top: 0; left: 0; overflow: hidden; }
        .player-wrapper { position: relative; width: 100%; flex-grow: 1; background: #000; overflow: hidden; display: flex; align-items: center; justify-content: center; cursor: none; }
        .player-wrapper.ui-on { cursor: default; }
        video { width: 100%; max-height: 100%; object-fit: contain; }

        .ui-element { transition: opacity 0.25s ease-in-out; opacity: 1; visibility: visible; }
        .ui-hidden { opacity: 0 !important; pointer-events: none !important; visibility: hidden !important; }

        .custom-controls { position: absolute; bottom: 0; left: 0; width: 100%; background: linear-gradient(transparent, rgba(0, 0, 0, 0.9) 30%); padding: 5px 12px calc(15px + env(safe-area-inset-bottom)) 12px; z-index: 100; box-sizing: border-box; }
        .controls-row { display: flex; align-items: center; justify-content: space-between; margin-top: 2px; }
        .control-group { display: flex; align-items: center; gap: 4px; }
        .control-btn { background: none; border: none; color: white; cursor: pointer; padding: 8px; display: flex; align-items: center; }
        .control-btn:disabled { opacity: 0.3; cursor: not-allowed; pointer-events: none; }
        .control-btn svg { width: 24px; height: 24px; fill: currentColor; }

        .seek-container { display: flex; align-items: center; gap: 8px; width: 100%; }
        .seek-bar { flex-grow: 1; accent-color: var(--accent); height: 20px; cursor: pointer; touch-action: none; margin: 0; }
        .mobile-time { display: none; font-family: monospace; font-size: 0.75em; color: #bbb; white-space: nowrap; }
        #centerFeedback {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.6); /* Darkened slightly */
            backdrop-filter: blur(4px);   /* Added blur for contrast */
            border-radius: 50%; width: 72px; height: 72px;
            display: flex; align-items: center; justify-content: center; z-index: 110;
            pointer-events: none; opacity: 1; transition: opacity 0.3s, transform 0.3s;
            border: 1px solid rgba(255,255,255,0.2); /* Added subtle rim */
        }

        .seek-ripple {
            position: absolute; top: 0; width: 40%; height: 100%;
            background: rgba(255,255,255,0.2); display: flex; flex-direction: column;
            align-items: center; justify-content: center; opacity: 0; pointer-events: none;
            z-index: 40; transition: opacity 0.2s;
        }
        .seek-ripple.left { left: 0; border-radius: 0 100% 100% 0; }
        .seek-ripple.right { right: 0; border-radius: 100% 0 0 100%; }
        .seek-text {
            color: white;
            font-weight: bold;
            font-size: 0.9em;
            margin-top: 5px;
            text-shadow: 0px 0px 4px rgba(0,0,0,0.9), 0px 0px 10px rgba(0,0,0,0.5); /* Fix for white backgrounds */
        }

        #customSubs { position: absolute; bottom: 10%; width: 100%; text-align: center; pointer-events: none; z-index: 10; transition: bottom 0.3s ease; }
        .sub-inner { color: white; font-size: 2.1em; text-shadow: 2px 2px 4px #000; font-weight: bold; padding: 0 10px; }
        .time-display { font-family: monospace; font-size: 0.75em; color: #bbb; white-space: nowrap; margin-left: 5px; }
        .subtitle-display { background: #111; padding: 10px 15px; color: white; min-height: 40px; font-size: 0.85em; border-top: 1px solid #333; z-index: 5; }
        .player-back { position: absolute; top: 8px; left: 8px; z-index: 150; text-shadow: 0 0 5px #000; font-size: 0.8em; text-decoration: none; color: white; }
        select.player-select { background:#222; color:white; border:none; border-radius:4px; padding:3px; font-size: 0.8em; cursor: pointer; }

        @media (max-width: 600px) {
            .time-display { display: none; }
            .mobile-time { display: block; }
            .control-btn { padding: 5px; }
            .control-group { gap: 2px; }
        }
    </style>
    """

    return render_template_string(f"""
    <!DOCTYPE html><html><head><title>Anisub Player</title><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">{KODI_STYLE}{player_styles}</head>
    <body>
        <div id="mainPlayerContainer">
            <a href="{BASE_PATH}/show/{{{{ folder_name | urlencode }}}}" class="back-btn player-back ui-element">← BACK</a>

            <div class="player-wrapper" id="videoArea" onclick="handleGlobalClick(event)" onmousemove="showUI()">
                <video id="videoPlayer" playsinline preload="metadata">
                    <source id="videoSource" src="{BASE_PATH}/stream/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}" type="video/mp4">
                    <track id="mainSub" kind="subtitles" src="{BASE_PATH}/sub/{{{{ folder_name | urlencode }}}}/{{{{ srt_name | urlencode }}}}" default>
                </video>

                <div id="centerFeedback" class="ui-element"><svg width="40" height="40" fill="white" viewBox="0 0 24 24" id="feedbackIcon"></svg></div>

                <div id="seekL" class="seek-ripple left"><svg width="40" height="40" fill="white" viewBox="0 0 24 24"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg><div class="seek-text" id="seekTextL">10 seconds</div></div>
                <div id="seekR" class="seek-ripple right"><svg width="40" height="40" fill="white" viewBox="0 0 24 24"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg><div class="seek-text" id="seekTextR">10 seconds</div></div>

                <div id="customSubs"><span class="sub-inner" id="subSpan"></span></div>
                <div id="previewContainer" style="position: absolute; bottom: 100px; left: 50%; transform: translateX(-50%); width: 140px; border: 1px solid var(--accent); border-radius: 4px; background: #000; display: none; flex-direction: column; z-index: 200; overflow: hidden;">
                    <img id="previewImg" style="width:100%; height:auto;" src=""><div id="previewTime" style="font-size:0.7em; text-align:center; padding:2px; color:var(--accent);">00:00</div>
                </div>

                <div class="custom-controls ui-element" id="controlsBar" onclick="event.stopPropagation()">
                    <div class="seek-container">
                        <input type="range" class="seek-bar" id="seekBar" value="0" step="0.1" oninput="updatePreview(this.value)" onchange="manualSeek(this.value)" onmousemove="handleHover(event)" onmouseenter="showPreview()" onmouseleave="hidePreview()" onmousedown="showPreview()" onmouseup="hidePreview()" ontouchstart="showPreview()" ontouchend="hidePreview()">
                        <div class="mobile-time"><span id="currTimeMob">0:00</span> / <span id="totalTimeMob">0:00</span></div>
                    </div>
                    <div class="controls-row">
                        <div class="control-group">
                            <button class="control-btn" onclick="location.href='{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ prev_ep | urlencode }}}}'" {{{{ 'disabled' if prev_ep is none else '' }}}}>
                                <svg viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
                            </button>
                            <button class="control-btn" onclick="togglePlay()" id="playBtn"><svg viewBox="0 0 24 24" id="playIcon"></svg></button>
                            <button class="control-btn" onclick="location.href='{BASE_PATH}/play/{{{{ folder_name | urlencode }}}}/{{{{ next_ep | urlencode }}}}'" {{{{ 'disabled' if next_ep is none else '' }}}}>
                                <svg viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/></svg>
                            </button>
                            <div class="time-display"><span id="currTime">0:00</span> / <span id="totalTime">0:00</span></div>
                        </div>
                        <div class="control-group">
                            <select id="resSelect" class="player-select" onchange="changeResolution(this.value)">
                                <option value="original">Orig</option>
                                {{% for res in available_res %}}
                                <option value="{{{{ res }}}}">{{{{ res }}}}</option>
                                {{% endfor %}}
                            </select>
                            <select id="speedSelect" class="player-select" onchange="video.playbackRate = this.value">
                                <option value="1" selected>1x</option><option value="1.5">1.5x</option><option value="2">2x</option>
                            </select>
                            <button class="control-btn" onclick="toggleCC()"><svg viewBox="0 0 24 24"><path d="M19 4H5c-1.11 0-2 .9-2 2v12c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-8 7H9.5V10h-2v4h2v-1H11v1c0 .55-.45 1-1 1H7c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c-.55 0 1 .45 1 1v1zm7 0h-1.5V10h-2v4h2v-1H18v1c0 .55-.45 1-1 1h-3c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1h3c.55 0 1 .45 1 1v1z"/></svg></button>
                            <button class="control-btn" onclick="toggleFullScreen()"><svg viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg></button>
                        </div>
                    </div>
                </div>
            </div>
            <div class="subtitle-display" id="subLog"><div id="subText">...</div></div>
        </div>
        <script>
            const video = document.getElementById('videoPlayer');
            const videoArea = document.getElementById('videoArea');
            const playIcon = document.getElementById('playIcon');
            const feedbackIcon = document.getElementById('feedbackIcon');
            const seekBar = document.getElementById('seekBar');
            const currTimeEl = document.getElementById('currTime'), currTimeMob = document.getElementById('currTimeMob');
            const totalTimeEl = document.getElementById('totalTime'), totalTimeMob = document.getElementById('totalTimeMob');
            const subSpan = document.getElementById('subSpan'), subText = document.getElementById('subText');
            const previewContainer = document.getElementById('previewContainer'), previewImg = document.getElementById('previewImg'), previewTime = document.getElementById('previewTime');
            const resSelect = document.getElementById('resSelect');

            let uiVisible = true;
            let uiTimeout = null;
            let clickTimer = null;
            let lastTapTime = 0;
            let currentSeekSum = 0;
            let seekResetTimer = null;

            function formatTime(sec) {{
                if (isNaN(sec)) return "0:00";
                const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.floor(sec % 60);
                return h > 0 ? `${{h}}:${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}` : `${{m}}:${{s.toString().padStart(2, '0')}}`;
            }}

            function showUI() {{
                uiVisible = true;
                videoArea.classList.add('ui-on');
                document.querySelectorAll('.ui-element').forEach(el => el.classList.remove('ui-hidden'));
                resetTimer();
            }}

            function hideUI() {{
                if (video.paused) return;
                uiVisible = false;
                videoArea.classList.remove('ui-on');
                document.querySelectorAll('.ui-element').forEach(el => el.classList.add('ui-hidden'));
            }}

            function resetTimer() {{
                if (uiTimeout) clearTimeout(uiTimeout);
                if (!video.paused) uiTimeout = setTimeout(hideUI, 3000);
            }}

            function forceUI(show) {{
                if (show) showUI(); else hideUI();
            }}

            function handleGlobalClick(e) {{
                const now = Date.now();
                const rect = videoArea.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                if (clickTimer) clearTimeout(clickTimer);

                if (now - lastTapTime < 300) {{
                    lastTapTime = now;
                    if (x < rect.width * 0.4) triggerYouTubeSeek('L');
                    else if (x > rect.width * 0.6) triggerYouTubeSeek('R');
                    return;
                }}

                lastTapTime = now;
                clickTimer = setTimeout(() => {{
                    const isCenter = x > rect.width * 0.35 && x < rect.width * 0.65 &&
                                   y > rect.height * 0.3 && y < rect.height * 0.7;

                    if (!uiVisible) {{
                        showUI();
                    }} else if (isCenter) {{
                        togglePlay(true);
                    }} else {{
                        hideUI();
                    }}
                }}, 250);
            }}

            function updatePlayIcon() {{
                const path = video.paused ? 'M8 5v14l11-7z' : 'M6 19h4V5H6v14zm8-14v14h4V5h-4z';
                const html = `<path d="${{path}}"/>`;
                playIcon.innerHTML = html;
                feedbackIcon.innerHTML = html;
            }}

            function togglePlay(autoHide = false) {{
                if (video.paused) {{
                    video.play();
                    if (autoHide) hideUI(); else resetTimer();
                }} else {{
                    video.pause();
                    showUI();
                }}
                updatePlayIcon();
            }}

            function triggerYouTubeSeek(dir) {{
                if (seekResetTimer) clearTimeout(seekResetTimer);
                currentSeekSum += 10;
                const el = document.getElementById(dir === 'L' ? 'seekL' : 'seekR');
                const txt = document.getElementById(dir === 'L' ? 'seekTextL' : 'seekTextR');
                video.currentTime += (dir === 'L' ? -10 : 10);
                txt.innerText = `${{currentSeekSum}} seconds`;
                el.style.opacity = '1';
                setTimeout(() => {{ el.style.opacity = '0'; }}, 600);
                seekResetTimer = setTimeout(() => {{ currentSeekSum = 0; }}, 1000);
                resetTimer();
            }}

            function changeResolution(res) {{
                const currentTime = video.currentTime;
                const isPaused = video.paused;
                localStorage.setItem('anisub_preferred_res', res);
                video.src = `{BASE_PATH}/stream/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}?res=${{res}}`;
                video.load();
                video.onloadedmetadata = () => {{
                    video.currentTime = currentTime;
                    if (!isPaused) video.play();
                }};
            }}

            function updatePreview(val) {{
                const targetTime = (val / 100) * video.duration;
                previewTime.innerText = formatTime(targetTime);
                previewContainer.style.left = val + "%";
                loadPreviewFrame(targetTime);
            }}

            let isPreviewLoading = false, pendingPreviewTime = null;
            function loadPreviewFrame(time) {{
                if (isNaN(time) || isPreviewLoading) {{ pendingPreviewTime = time; return; }}
                isPreviewLoading = true;
                const url = `{BASE_PATH}/preview/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}?t=${{time}}`;
                const img = new Image();
                img.onload = () => {{
                    previewImg.src = url; isPreviewLoading = false;
                    if (pendingPreviewTime) {{ let t = pendingPreviewTime; pendingPreviewTime = null; loadPreviewFrame(t); }}
                }};
                img.src = url;
            }}

            function handleHover(e) {{
                const rect = seekBar.getBoundingClientRect();
                const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
                updatePreview(Math.min(Math.max(0, x / rect.width), 1) * 100);
            }}

            function showPreview() {{ previewContainer.style.display = 'flex'; }}
            function hidePreview() {{ setTimeout(() => {{ previewContainer.style.display = 'none'; }}, 100); }}
            function manualSeek(val) {{ video.currentTime = (val / 100) * video.duration; resetTimer(); }}
            function toggleCC() {{ const t = video.textTracks[0]; t.mode = (t.mode === 'disabled') ? 'hidden' : 'disabled'; if(t.mode==='disabled') subSpan.innerText=""; }}

            function toggleFullScreen() {{
                if (!document.fullscreenElement) {{
                    if (videoArea.requestFullscreen) videoArea.requestFullscreen();
                    else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
                }} else document.exitFullscreen();
            }}

            video.addEventListener('timeupdate', () => {{
                seekBar.value = (video.currentTime / video.duration) * 100 || 0;
                const f = formatTime(video.currentTime);
                currTimeEl.innerText = currTimeMob.innerText = f;
                if (Math.floor(video.currentTime) % 10 === 0) {{
                    const h = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
                    h["{folder_name}"] = {{ last_ep: "{video_name}", time: video.currentTime }};
                    localStorage.setItem('anisub_history', JSON.stringify(h));
                }}
            }});

            video.addEventListener('loadedmetadata', () => {{
                const f = formatTime(video.duration);
                totalTimeEl.innerText = totalTimeMob.innerText = f;
                const h = JSON.parse(localStorage.getItem('anisub_history') || '{{}}');
                if (h["{folder_name}"]?.last_ep === "{video_name}") video.currentTime = h["{folder_name}"].time;
                updatePlayIcon();
                resetTimer();
            }});

            window.addEventListener('DOMContentLoaded', () => {{
                const prefRes = localStorage.getItem('anisub_preferred_res') || '720p';
                if (Array.from(resSelect.options).some(opt => opt.value === prefRes)) {{
                    resSelect.value = prefRes;
                    video.src = `{BASE_PATH}/stream/{{{{ folder_name | urlencode }}}}/{{{{ video_name | urlencode }}}}?res=${{prefRes}}`;
                }}
                updatePlayIcon();
            }});

            const track = video.textTracks[0];
            track.mode = 'hidden';
            track.oncuechange = function() {{
                if (this.activeCues?.length > 0) subSpan.innerText = subText.innerText = this.activeCues[0].text;
                else subSpan.innerText = "";
            }};

            document.addEventListener('keydown', (e) => {{
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
                showUI();
                switch (e.key) {{
                    case 'ArrowLeft': e.preventDefault(); triggerYouTubeSeek('L'); break;
                    case 'ArrowRight': e.preventDefault(); triggerYouTubeSeek('R'); break;
                    case ' ': e.preventDefault(); togglePlay(); break;
                    case 'f': e.preventDefault(); toggleFullScreen(); break;
                 }}
            }});
        </script>
    </body></html>
    """, folder_name=folder_name, video_name=video_name, srt_name=srt_name, prev_ep=prev_ep, next_ep=next_ep, available_res=available_res)

@anisub_bp.route('/stream/<path:folder_name>/<path:video_name>')
def stream_video(folder_name, video_name):
    folder_name = unquote(folder_name)
    video_name = unquote(video_name)

    # Get the 'res' parameter from the URL (?res=240p)
    requested_res = request.args.get('res', 'original')

    # Base directory for the show
    folder_path = os.path.join(BASE_DIR, folder_name)

    # Determine the actual file path
    if requested_res != 'original':
        # Look inside the subfolder (e.g., "Yuru Camp/240p/video.mp4")
        target_path = os.path.join(folder_path, requested_res, video_name)

        # Fallback to original if the specific resolution file doesn't exist
        if not os.path.exists(target_path):
            target_path = os.path.join(folder_path, video_name)
    else:
        target_path = os.path.join(folder_path, video_name)

    if not os.path.exists(target_path):
        abort(404)

    # Use your existing range-request helper or send_file
    return send_from_directory(os.path.dirname(target_path), os.path.basename(target_path))

@anisub_bp.route('/poster_file/<path:folder_name>/<path:filename>')
def serve_poster(folder_name, filename):
    folder_name, filename = unquote(folder_name), unquote(filename)
    path = os.path.join(BASE_DIR, folder_name, filename)
    if not os.path.exists(path): abort(404)
    # Automatically detect if it's jpg, png, or webp
    mime = mimetypes.guess_type(path)[0] or 'image/jpeg'
    return send_file(path, mimetype=mime)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
