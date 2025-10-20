import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.config_dir = os.getenv("CONFIG_DIR", "config")
        self.settings_filename = os.getenv("SETTINGS_FILENAME", "settings.yml")
        working_dir = os.getenv("WORKING_DIR", "working_dir")
        self.working_dir = Path(working_dir)
        self.docker_registry = os.getenv("DOCKER_REGISTRY")
        self.docker_username = os.getenv("DOCKER_USERNAME")
        self.docker_password = os.getenv("DOCKER_PASSWORD")


load_dotenv()
settings = Settings()
