"""Runtime configuration, read from environment variables (12-factor style).

On Render you set these in the dashboard (Environment tab) or in render.yaml. Locally
they fall back to the defaults below, so the app runs with zero setup.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Stitch Service"
    version: str = "1.0.0"

    # Where uploads and rendered results live. Anchored to the repo so cwd never matters.
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"

    # Simulated extra work time (seconds) so you can watch a job poll. 0 = as fast as possible.
    stitch_delay_seconds: float = 0.0

    # Comma-separated list, or "*" for any origin.
    cors_allow_origins: str = "*"

    # Reject uploads larger than this (bytes). Default 10 MB.
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def results_dir(self) -> Path:
        return self.data_dir / "results"


settings = Settings()
