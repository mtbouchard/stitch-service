"""Runtime configuration, read from environment variables (12-factor style)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Stitch Service"
    version: str = "2.0.0"

    data_dir: Path = REPO_ROOT / "data"

    # The no-arg compute script (run via create_subprocess_exec). Anchored to the repo.
    script_path: Path = REPO_ROOT / "stitch.py"

    cors_allow_origins: str = "*"
    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    # The script reads HARDCODED names here; the API stages the chosen images into them.
    @property
    def stage_dir(self) -> Path:
        return self.data_dir / "stage"

    @property
    def stage1_path(self) -> Path:
        return self.stage_dir / "s1.jpg"

    @property
    def stage2_path(self) -> Path:
        return self.stage_dir / "s2.jpg"

    @property
    def output_path(self) -> Path:
        return self.stage_dir / "output.jpg"


settings = Settings()
