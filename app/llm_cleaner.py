import asyncio
import os

from groq import AsyncGroq

SYSTEM_PROMPT = """\
You are a text preprocessor for text-to-speech audio conversion.
Your job is to clean and prepare document text so it sounds natural and clear when read aloud.

Rules:
- Remove any remaining page numbers, running headers, or footers
- Fix sentences broken by PDF or document line wrapping
- Expand abbreviations naturally (Dr. -> Doctor, vs. -> versus, e.g. -> for example, etc. -> and so on, i.e. -> that is)
- Convert symbols to spoken words (§ -> Section, % -> percent, & -> and, # -> number, @ -> at)
- Ensure punctuation creates natural pauses — add commas or periods only where clearly missing
- Preserve paragraph breaks as natural pauses
- Do NOT summarize, add commentary, skip content, or change the meaning in any way
- Return ONLY the cleaned text — no explanations, labels, or prefixes\
"""


def _get_client() -> AsyncGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set. "
            "Add it to your .env file locally or Railway environment variables."
        )
    return AsyncGroq(api_key=api_key)


async def _clean_chunk(text: str, client: AsyncGroq, semaphore: asyncio.Semaphore) -> str:
    """Send one chunk to Groq for cleaning. Falls back to original text on any error."""
    async with semaphore:
        try:
            response = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            cleaned = response.choices[0].message.content.strip()
            return cleaned if cleaned else text
        except Exception:
            return text  # Silently fall back to original if Groq fails


async def clean_chunks_with_llm(
    chunks: list[str],
    progress_callback=None,
) -> list[str]:
    """
    Clean all text chunks through Groq LLM concurrently.
    Uses a semaphore to stay within Groq's rate limits (5 concurrent requests).
    If GROQ_API_KEY is not set, returns chunks unchanged.
    """
    if not os.environ.get("GROQ_API_KEY"):
        return chunks

    client = _get_client()
    semaphore = asyncio.Semaphore(5)
    total = len(chunks)
    results: list[str] = [""] * total

    async def process(i: int, chunk: str):
        results[i] = await _clean_chunk(chunk, client, semaphore)
        if progress_callback:
            await progress_callback(i + 1, total)

    await asyncio.gather(*[process(i, chunk) for i, chunk in enumerate(chunks)])
    return results
