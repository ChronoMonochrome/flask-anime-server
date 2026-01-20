# Anime Library Server

<video src="https://github.com/user-attachments/assets/e044ec1b-4697-4d19-81ae-948cb504b6b1" controls="controls" style="max-width: 730px;">
</video>

A Flask-powered media server for local anime collections, optimized for both desktop and mobile viewing with a focus on high-readability subtitles and seamless navigation.

## 🛠️ Project Structure


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

## ⚙️ Technical Details

-   **Backend:** Python / Flask
    
-   **Frontend:** HTML5, CSS3 (Flexbox/Grid), Vanilla JavaScript
    
-   **Subtitle Processing:** On-the-fly SRT to VTT conversion with charset error handling.


----------

## 📝 Subtitle Formatting Note

The player is optimized for large-scale text rendering. You can adjust the subtitle size in the `player_styles` section of `app.py`:

CSS

```
.sub-inner { 
    font-size: 3.2em; /* Increase/decrease this for size */
    text-shadow: 2px 2px 4px #000; 
}
