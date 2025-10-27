import shutil
from pathlib import Path

from docker_image_builder.logger import get_logger
from docker_image_builder.settings import settings
from docker_image_builder.workspace.image_settings import ImageSettings

logger = get_logger(__name__)

TEMPLATE_FILE = Path(__file__).resolve().parent.parent / "templates/settings_template.yml"  # path to your template file


def ensure_workspace() -> list[ImageSettings]:
    """Scan the config directory for build folders and ensure settings.yml files exist."""
    config_dir = Path(settings.config_dir)
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created config directory: {settings.config_dir}")

    image_dirs: list[ImageSettings] = []

    for entry in config_dir.iterdir():
        if entry.is_dir():
            image_directory = Path(entry)
            settings_file = image_directory / settings.settings_filename

            if not settings_file.exists():
                if TEMPLATE_FILE.exists():
                    try:
                        shutil.copy(TEMPLATE_FILE, settings_file)
                        logger.info(f"Copied template settings.yml to {settings_file}")
                    except Exception as e:
                        logger.error(f"Failed to copy template to {settings_file}: {e}")
                else:
                    logger.error(f"Template file {TEMPLATE_FILE} not found. Cannot create settings.yml.")

            image_dirs.append(ImageSettings(settings_file))

    if not image_dirs:
        logger.warning("No image folders found in config directory.")

    return image_dirs
