import os
import time
from pathlib import Path
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirCreatedEvent, DirDeletedEvent, FileModifiedEvent, FileDeletedEvent

from docker_image_builder.logger import get_logger
from docker_image_builder.tasks import scheduler
from docker_image_builder.settings import settings
from docker_image_builder.workspace.image_settings import ImageSettings
from docker_image_builder.workspace.workspace import ensure_workspace

logger = get_logger(__name__)

TEMPLATE_FILE = "templates/settings_template.yml"  # path to your template file


class DataEventHandler(FileSystemEventHandler):
    """Handle filesystem events in the data directory."""

    def on_created(self, event):
        if isinstance(event, DirCreatedEvent):
            folder_path = Path(event.src_path)
            logger.info(f"New folder detected: {folder_path.name}")
            settings_path = folder_path / settings.settings_filename

            if not os.path.exists(settings_path):
                if os.path.exists(TEMPLATE_FILE):
                    try:
                        shutil.copy(TEMPLATE_FILE, settings_path)
                        logger.info(f"Copied template settings.yml to {settings_path}")
                    except Exception as e:
                        logger.error(f"Failed to copy template to {settings_path}: {e}")
                else:
                    logger.error(f"Template file {TEMPLATE_FILE} not found. Cannot create settings.yml.")

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent):
            if os.path.basename(event.src_path) == settings.settings_filename:
                settings_path = Path(event.src_path)
                image_settings = ImageSettings(settings_path)
                folder_name = os.path.dirname(event.src_path)
                logger.info(f"settings.yml changed in {folder_name}")

                try:
                    scheduler.add_or_update_job(image_settings)

                except Exception as e:
                    logger.error(f"Failed to process settings.yml for {folder_name}: {e}")

    def on_deleted(self, event):
        # Directory deleted → remove scheduled job
        if isinstance(event, DirDeletedEvent):
            folder_path = Path(event.src_path)
            logger.info(f"Folder deleted: {folder_path}, removing scheduled job if exists")
            scheduler.remove_job(folder_path)

        # settings.yml deleted → recreate from template
        if isinstance(event, FileDeletedEvent):
            if os.path.basename(event.src_path) == settings.settings_filename:
                folder_path = os.path.dirname(event.src_path)
                logger.info(f"settings.yml deleted in {folder_path}, recreating from template")
                settings_path = os.path.join(folder_path, settings.settings_filename)
                if os.path.exists(TEMPLATE_FILE):
                    try:
                        shutil.copy(TEMPLATE_FILE, settings_path)
                        logger.info(f"Copied template settings.yml to {settings_path}")
                    except Exception as e:
                        logger.error(f"Failed to copy template to {settings_path}: {e}")
                else:
                    logger.error(f"Template file {TEMPLATE_FILE} not found. Cannot recreate settings.yml.")


def start_watcher():
    """Start monitoring the data folder for new folders and settings.yml changes."""
    logger.info(f"Starting folder watcher on: {settings.data_dir}")
    images_settings = ensure_workspace()

    scheduler.start()

    for image_settings in images_settings:
        scheduler.add_or_update_job(image_settings)

    event_handler = DataEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=settings.data_dir, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping folder watcher...")
        observer.stop()
    observer.join()
