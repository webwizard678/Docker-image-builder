import os
import shutil
from pathlib import Path

from docker_image_builder.logger import get_logger
from docker_image_builder.settings import settings
from docker_image_builder.workspace.image_settings import ImageSettings

logger = get_logger(__name__)

TEMPLATE_FILE = "settings_template.yml"  # path to your template file


def ensure_workspace() -> list[ImageSettings]:
    """Scan the data directory for build folders and ensure settings.yml files exist."""
    if not os.path.exists(settings.data_dir):
        os.makedirs(settings.data_dir)
        logger.info(f"Created data directory: {settings.data_dir}")

    image_dirs: list[ImageSettings] = []

    for entry in os.scandir(settings.data_dir):
        if entry.is_dir():
            image_directory = Path(entry.path)
            settings_file = image_directory / settings.settings_filename

            if not os.path.exists(settings_file):
                if os.path.exists(TEMPLATE_FILE):
                    try:
                        shutil.copy(TEMPLATE_FILE, settings_file)
                        logger.info(f"Copied template settings.yml to {settings_file}")
                    except Exception as e:
                        logger.error(f"Failed to copy template to {settings_file}: {e}")
                else:
                    logger.error(f"Template file {TEMPLATE_FILE} not found. Cannot create settings.yml.")

            image_dirs.append(ImageSettings(settings_file))

    if not image_dirs:
        logger.warning("No image folders found in data directory.")

    return image_dirs
