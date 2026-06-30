from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Clutch — Last-Minute Life Saver"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ALLOWED_ORIGINS: list[str] = ["*"]
    # Gemini via AI Studio Developer API. Key from https://aistudio.google.com/apikey
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"  # fall back to "gemini-2.0-flash" if quota-limited
    TIMEZONE: str = "Asia/Kolkata"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
