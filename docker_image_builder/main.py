from docker_image_builder.docker.builder import DockerBuilder
from docker_image_builder.logger import get_logger
from docker_image_builder.watcher import start_watcher

logger = get_logger(__name__)


def main() -> None:
    """Main entry point for the Docker image builder."""
    logger.info("Starting Docker Image Builder App...")

    DockerBuilder()  # Initialize Docker client early to catch connection issues

    start_watcher()

    logger.info("Application stopped.")


if __name__ == "__main__":
    main()
