# 侍の道 (Samurai no Michi) - Anime Library Server

A Flask-powered media server for local anime collections, optimized for both desktop and mobile viewing with a focus on high-readability subtitles and seamless navigation.

## 🚀 Features

-   **Custom Video Engine:** Built on top of HTML5 video but extended with a custom UI that stays out of your way.
    
-   **Smart Subtitles:** Automatic conversion of `.srt` files to WebVTT. Subtitles are rendered in a large, high-contrast format for easy reading.
    
-   **Interactive Controls:**
    
    -   **Double-Tap Seek:** Quickly skip 10 seconds forward or backward by double-clicking the sides of the video.
        
    -   **Playback Speed:** Adjustable speed (0.5x to 2x) directly from the player.
        
    -   **Dynamic UI:** Controls and cursor auto-hide during playback and reappear on mouse movement or tap.
        
    -   **Last Phrase Tracking:** A dedicated area below the player shows the most recently spoken line, perfect for language learners.
    
-   **Persistent Progress:** Saves your watch history and timestamps in local storage to resume where you left off.
    

----------

## 🛠️ Project Structure

Plaintext

```
.
├── app.py                # Main Flask application and Player logic
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container definition
└── anime_library/        # Your media root
    └── Series_Name/      # Folder per show
        ├── Episode_01.mp4
        ├── Episode_01.srt
        └── ...

```

----------

## 🐳 Quick Start with Docker

The easiest way to run the server is using Docker.

1.  **Prepare your media:** Place your anime folders inside a directory named `anime_library`.
    
2.  **Configure Environment:** Ensure the `BASE_DIR` in `app.py` points to your internal container path.
    
3.  **Launch:**
    
    Bash
    
    ```
    docker-compose up -d
    
    ```
    
4.  **Access:** Open your browser and navigate to `http://localhost:5000/侍の道`.
    

----------

## 🎮 Player Shortcuts & Gestures

**Action**

**Input**

**Play/Pause**

Single Click / Tap Center

**Seek -10s**

Double Click Left 33% of Screen

**Seek +10s**

Double Click Right 33% of Screen

**Toggle UI**

Move Mouse / Single Tap

**Exit Fullscreen**

ESC Key / Fullscreen Button

----------

## ⚙️ Technical Details

-   **Backend:** Python / Flask
    
-   **Frontend:** HTML5, CSS3 (Flexbox/Grid), Vanilla JavaScript
    
-   **Subtitle Processing:** On-the-fly SRT to VTT conversion with charset error handling.
    
-   **Routing:** Uses a Flask Blueprint with a custom URL prefix (`/侍の道`) to avoid collisions with other services.
    

----------

## 📝 Subtitle Formatting Note

The player is optimized for large-scale text rendering. You can adjust the subtitle size in the `player_styles` section of `app.py`:

CSS

```
.sub-inner { 
    font-size: 3.2em; /* Increase/decrease this for size */
    text-shadow: 2px 2px 4px #000; 
}
