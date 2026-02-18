import asyncio
import os
import subprocess
import edge_tts


VOICES = {
    "en-US-AriaNeural": "Aria (US Female)",
    "en-US-GuyNeural": "Guy (US Male)",
    "en-US-JennyNeural": "Jenny (US Female)",
    "en-GB-SoniaNeural": "Sonia (UK Female)",
    "en-GB-RyanNeural": "Ryan (UK Male)",
    "en-AU-NatashaNeural": "Natasha (AU Female)",
}


async def text_chunk_to_audio(text: str, voice: str, output_path: str) -> None:
    """Convert a single text chunk to an audio file using edge-tts."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


async def convert_chunks_to_audio(
    chunks: list[str],
    voice: str,
    temp_dir: str,
    job_id: str,
    progress_callback=None,
) -> list[str]:
    """Convert all text chunks to individual audio files."""
    audio_files = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        chunk_path = os.path.join(temp_dir, f"{job_id}_chunk_{i:04d}.mp3")
        await text_chunk_to_audio(chunk, voice, chunk_path)
        audio_files.append(chunk_path)

        if progress_callback:
            await progress_callback(i + 1, total)

    return audio_files


def merge_audio_files(audio_files: list[str], output_path: str) -> None:
    """Merge multiple mp3 files into a single audiobook file using ffmpeg."""
    # Write a concat list file for ffmpeg
    list_path = output_path + ".txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for path in audio_files:
            # ffmpeg concat demuxer requires forward slashes and escaped paths
            safe = path.replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe}'\n")

    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-ac", "1",        # mono (sufficient for speech)
                "-ar", "22050",    # 22kHz sample rate (sufficient for speech)
                "-b:a", "32k",     # 32kbps — great quality for speech, small file
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass


def cleanup_chunks(audio_files: list[str]) -> None:
    """Remove temporary chunk files after merging."""
    for path in audio_files:
        try:
            os.remove(path)
        except OSError:
            pass
