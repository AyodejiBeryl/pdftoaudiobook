import asyncio
import os
import shutil
import subprocess
import edge_tts


def _find_ffmpeg() -> str:
    """Locate the ffmpeg binary, checking PATH and common install locations."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    candidates = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        r"C:\Users\ayode\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise RuntimeError(
        "ffmpeg not found. Install it with: winget install ffmpeg (Windows) "
        "or apt install ffmpeg (Linux)"
    )


async def get_voices() -> list[dict]:
    """Fetch all available edge-tts voices grouped by language."""
    voices = await edge_tts.list_voices()
    result = []
    for v in sorted(voices, key=lambda x: (x["Locale"], x["ShortName"])):
        result.append({
            "id": v["ShortName"],
            "label": v["FriendlyName"],
            "language": v["Locale"],
            "language_name": _locale_to_name(v["Locale"]),
            "gender": v["Gender"],
        })
    return result


def _locale_to_name(locale: str) -> str:
    """Convert a locale code to a human-readable language name."""
    mapping = {
        "af": "Afrikaans", "am": "Amharic", "ar": "Arabic",
        "az": "Azerbaijani", "bg": "Bulgarian", "bn": "Bengali",
        "bs": "Bosnian", "ca": "Catalan", "cs": "Czech",
        "cy": "Welsh", "da": "Danish", "de": "German",
        "el": "Greek", "en": "English", "es": "Spanish",
        "et": "Estonian", "fa": "Persian", "fi": "Finnish",
        "fil": "Filipino", "fr": "French", "ga": "Irish",
        "gl": "Galician", "gu": "Gujarati", "he": "Hebrew",
        "hi": "Hindi", "hr": "Croatian", "hu": "Hungarian",
        "hy": "Armenian", "id": "Indonesian", "is": "Icelandic",
        "it": "Italian", "ja": "Japanese", "jv": "Javanese",
        "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
        "kn": "Kannada", "ko": "Korean", "lo": "Lao",
        "lt": "Lithuanian", "lv": "Latvian", "mk": "Macedonian",
        "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi",
        "ms": "Malay", "mt": "Maltese", "my": "Burmese",
        "nb": "Norwegian", "ne": "Nepali", "nl": "Dutch",
        "or": "Odia", "pa": "Punjabi", "pl": "Polish",
        "ps": "Pashto", "pt": "Portuguese", "ro": "Romanian",
        "ru": "Russian", "si": "Sinhala", "sk": "Slovak",
        "sl": "Slovenian", "so": "Somali", "sq": "Albanian",
        "sr": "Serbian", "su": "Sundanese", "sv": "Swedish",
        "sw": "Swahili", "ta": "Tamil", "te": "Telugu",
        "th": "Thai", "tr": "Turkish", "uk": "Ukrainian",
        "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese",
        "wuu": "Chinese (Wu)", "yue": "Chinese (Cantonese)",
        "yo": "Yoruba", "zh": "Chinese (Mandarin)", "zu": "Zulu",
    }
    lang_code = locale.split("-")[0].lower()
    return mapping.get(lang_code, locale)


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
    list_path = output_path + ".txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for path in audio_files:
            safe = path.replace("\\", "/").replace("'", "\\'")
            f.write(f"file '{safe}'\n")

    try:
        subprocess.run(
            [
                _find_ffmpeg(), "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-ac", "1",
                "-ar", "22050",
                "-b:a", "32k",
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
