from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict

from docker_image_builder.workspace.image_builder import ImageBuilder
from docker_image_builder.logger import get_logger
from docker_image_builder.workspace.image_settings import ImageSettings

logger = get_logger(__name__)

scheduler = BackgroundScheduler()
scheduled_jobs: Dict[Path, str] = {}  # folder_path -> job_id


def start() -> None:
    scheduler.start()
    logger.info("Scheduler started.")


def add_or_update_job(image_settings: ImageSettings) -> None:
    """
    Add or update a scheduled job based on the image settings.
    Also performs an initial build when scheduling the job.
    """
    folder_path = image_settings.workspace_path
    job_id = folder_path.name
    cron_expr = image_settings.cron_expr.strip()

    if job_id in scheduled_jobs:
        scheduler.remove_job(job_id)
        logger.info(f"Removed existing scheduled job for {folder_path}")

    if not cron_expr:
        logger.info(f"No schedule set for {folder_path}, skipping scheduling")
        scheduled_jobs.pop(folder_path, None)
        return

    fields = cron_expr.split()
    if len(fields) != 5:
        logger.error(f"Invalid cron expression '{cron_expr}' for folder {folder_path}")
        return

    minute, hour, day, month, day_of_week = fields
    trigger = CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)

    image_builder = ImageBuilder(image_settings)

    scheduler.add_job(
        func=image_builder.build,
        trigger=trigger,
        args=[],
        id=job_id,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduled_jobs[folder_path] = job_id
    logger.info(f"Scheduled job for {folder_path} with tag '{image_settings.tag}' at '{cron_expr}'")

    image_builder.build()  # Initial build on scheduling


def remove_job(folder_path: Path) -> None:
    job_id = scheduled_jobs.get(folder_path)
    if job_id:
        try:
            scheduler.remove_job(job_id)
            scheduled_jobs.pop(folder_path, None)
            logger.info(f"Removed scheduled job for {folder_path}")
        except Exception as e:
            logger.error(f"Failed to remove job for {folder_path}: {e}")
