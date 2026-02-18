import fitz  # PyMuPDF
import re


def extract_text(pdf_path: str) -> str:
    """Extract and clean text from a PDF file."""
    doc = fitz.open(pdf_path)
    pages_text = []

    for page in doc:
        text = page.get_text("text")
        pages_text.append(text)

    doc.close()
    raw_text = "\n".join(pages_text)
    return clean_text(raw_text)


def clean_text(text: str) -> str:
    """Remove noise commonly found in extracted PDF text."""
    # Remove excessive whitespace and blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove hyphenation at line breaks (e.g., "some-\nword" -> "someword")
    text = re.sub(r'-\n', '', text)
    # Join lines that are not paragraph breaks
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split text into chunks at sentence boundaries for TTS processing."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current.strip())
            # If a single sentence exceeds max_chars, split it hard
            if len(sentence) > max_chars:
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
            else:
                current = sentence

    if current:
        chunks.append(current.strip())

    return chunks
