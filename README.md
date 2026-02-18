# PDF to Audiobook

Convert any PDF into a listenable audiobook using Microsoft Edge neural voices (free, no API key).

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg (required by pydub for audio merging)

Download from https://ffmpeg.org/download.html and add it to your PATH,
or install via winget:

```bash
winget install ffmpeg
```

### 3. Run the app

```bash
python run.py
```

### 4. Open in browser

- **PC:** http://localhost:8000
- **iPhone:** The terminal will display your local IP, e.g. http://192.168.1.x:8000
  - Make sure your iPhone and PC are on the same WiFi network

## Notes

- Conversion requires an internet connection (edge-tts fetches audio from Microsoft)
- Large PDFs may take a few minutes to convert
- Output is saved as an MP3 file
