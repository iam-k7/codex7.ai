import os
import tempfile
from groq import Groq
from dotenv import load_dotenv

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def transcribe_with_groq(video_path: str, language: str = "en"):
    """
    Uses Groq Whisper Large v3 (FREE tier).
    """
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY not set")

    # Groq expects audio, so we send video directly (it extracts audio)
    with open(video_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3",
            language=language,
            response_format="verbose_json"
        )

    return transcription
