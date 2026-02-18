import os
import socket
import uvicorn
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present (local dev); Railway injects vars directly

# Local Windows: ensure ffmpeg is on PATH
FFMPEG_BIN = r"C:\Users\ayode\ffmpeg\bin"
if os.path.exists(FFMPEG_BIN) and FFMPEG_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_BIN + os.pathsep + os.environ.get("PATH", "")


def get_local_ip():
    """Get the machine's local network IP for mobile access."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    # Railway (and most cloud platforms) set the PORT env variable
    port = int(os.environ.get("PORT", 8000))
    is_cloud = "PORT" in os.environ

    if is_cloud:
        print(f"\n PDF to Audiobook — running on port {port}\n")
    else:
        local_ip = get_local_ip()
        print("\n" + "=" * 50)
        print("  PDF to Audiobook")
        print("=" * 50)
        print(f"  Local:   http://localhost:{port}")
        print(f"  iPhone:  http://{local_ip}:{port}")
        print("  (Both devices must be on the same WiFi)")
        print("=" * 50 + "\n")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
