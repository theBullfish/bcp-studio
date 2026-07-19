import os


class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    # Directory where source media lands and where derived variants are written.
    MEDIA_ROOT = os.getenv("MEDIA_ROOT", "/data/media")
    # Whether ffmpeg-based real processing is enabled (auto-detected at runtime).
    ENABLE_FFMPEG = os.getenv("ENABLE_FFMPEG", "auto")

    @property
    def has_anthropic(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)


config = Config()
