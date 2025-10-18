import yaml
from pathlib import Path

from docker_image_builder.settings import settings


class ImageSettings:
    """Image-specific configuration loaded from a settings.yml file."""

    def __init__(self, settings_file: Path) -> None:
        self.settings_file: Path = settings_file.resolve()
        settings_folder = settings_file if settings_file.is_dir() else settings_file.parent
        workspace_path = settings.working_dir / settings_folder.name
        self.github_repo = None
        self.github_branch = None
        self.tag = None
        self.cron_expr = None
        self._load_settings()

        self.workspace_path: Path = workspace_path.resolve() / Path(self.github_repo).stem if self.github_repo else workspace_path.resolve()

    def _load_settings(self) -> None:
        if not self.settings_file.exists():
            return  # silently skip if no settings.yml
        with open(self.settings_file, "r") as f:
            data = yaml.safe_load(f) or {}
        self.github_repo = data.get("github_repo", self.github_repo)
        self.github_branch = data.get("github_branch", self.github_branch)
        tag = data.get("tag", self.tag)
        full_tag = f"{settings.docker_registry}/{tag}"
        self.tag = full_tag
        self.cron_expr = data.get("schedule", self.cron_expr)

    def refresh(self) -> None:
        """Reload settings from the YAML file."""
        self._load_settings()
