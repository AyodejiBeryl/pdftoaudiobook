import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any

import aiofiles
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.pdf_parser import extract_text, chunk_text, SUPPORTED_EXTENSIONS
from app.tts_engine import (
    get_voices,
    convert_chunks_to_audio,
    merge_audio_files,
    cleanup_chunks,
)
from app.llm_cleaner import clean_chunks_with_llm

BASE_DIR = Path(__file__).parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Zelos Audiobook Converter")

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
JOB_TTL_SECONDS = 2 * 60 * 60       # 2 hours

# In-memory job store: {job_id: {..., "created_at": float}}
jobs: Dict[str, Any] = {}

# Cache voices so we don't re-fetch on every request
_voices_cache: list[dict] | None = None


@app.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(_periodic_cleanup())


@app.get("/api/voices")
async def api_get_voices():
    global _voices_cache
    if _voices_cache is None:
        _voices_cache = await get_voices()
    return {"voices": _voices_cache}


@app.post("/api/convert")
async def convert(
    file: UploadFile = File(...),
    voice: str = Form(default="en-US-AriaNeural"),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_BYTES // 1024 // 1024} MB."
        )

    job_id = str(uuid.uuid4())
    file_path = UPLOADS_DIR / f"{job_id}{ext}"

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    jobs[job_id] = {
        "status": "processing",
        "phase": "extracting",
        "progress": 0,
        "total": 0,
        "filename": file.filename,
        "created_at": time.time(),
        "error": None,
    }

    asyncio.create_task(_run_conversion(job_id, file_path, voice))
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/api/download/{job_id}")
def download(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Audio not ready yet.")

    output_path = OUTPUTS_DIR / f"{job_id}.mp3"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output file missing.")

    stem = Path(job["filename"]).stem
    return FileResponse(
        path=str(output_path),
        media_type="audio/mpeg",
        filename=f"{stem}.mp3",
    )


async def _run_conversion(job_id: str, pdf_path: Path, voice: str):
    """Background task: extract → LLM clean → TTS → merge."""
    try:
        # Phase 1: Extract text
        jobs[job_id]["phase"] = "extracting"
        text = extract_text(str(pdf_path))
        if not text.strip():
            jobs[job_id].update({"status": "error", "error": "No readable text found in the document."})
            return

        chunks = chunk_text(text)
        jobs[job_id]["total"] = len(chunks)

        # Phase 2: LLM cleaning (skipped gracefully if no API key)
        jobs[job_id].update({"phase": "cleaning", "progress": 0})

        async def on_clean_progress(done: int, total: int):
            jobs[job_id]["progress"] = done

        chunks = await clean_chunks_with_llm(chunks, progress_callback=on_clean_progress)

        # Phase 3: TTS conversion
        jobs[job_id].update({"phase": "converting", "progress": 0})

        async def on_tts_progress(done: int, total: int):
            jobs[job_id]["progress"] = done

        chunk_files = await convert_chunks_to_audio(
            chunks, voice, str(UPLOADS_DIR), job_id,
            progress_callback=on_tts_progress,
        )

        # Phase 4: Merge
        jobs[job_id]["phase"] = "merging"
        output_path = OUTPUTS_DIR / f"{job_id}.mp3"
        merge_audio_files(chunk_files, str(output_path))
        cleanup_chunks(chunk_files)

        jobs[job_id]["status"] = "done"

    except Exception as e:
        jobs[job_id].update({"status": "error", "error": str(e)})
    finally:
        try:
            pdf_path.unlink()
        except OSError:
            pass


async def _periodic_cleanup():
    """Remove jobs and their output files older than JOB_TTL_SECONDS every 30 minutes."""
    while True:
        await asyncio.sleep(30 * 60)
        cutoff = time.time() - JOB_TTL_SECONDS
        expired = [jid for jid, j in jobs.items() if j.get("created_at", 0) < cutoff]
        for jid in expired:
            output = OUTPUTS_DIR / f"{jid}.mp3"
            try:
                output.unlink(missing_ok=True)
            except OSError:
                pass
            jobs.pop(jid, None)


# Serve frontend — must be last
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
