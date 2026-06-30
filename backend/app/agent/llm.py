from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings


@lru_cache(maxsize=2)
def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    # Gemini via the AI Studio Developer API (API-key based).
    # Get a key at https://aistudio.google.com/apikey and set GOOGLE_API_KEY.
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
    )
