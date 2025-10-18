import platform
import shutil
from pathlib import Path
import docker
from docker.errors import BuildError, APIError
from docker.models.images import Image
from typing import Optional

from docker_image_builder.logger import get_logger
from docker_image_builder.settings import settings
from docker_image_builder.workspace.image_settings import ImageSettings


def get_targetplatform():
    system = platform.system().lower()  # 'linux', 'darwin', 'windows'
    machine = platform.machine().lower()  # 'x86_64', 'arm64', 'aarch64', etc.

    # Normalize machine to Docker platform architecture names
    arch_map = {
        'x86_64': 'amd64',
        'amd64': 'amd64',
        'aarch64': 'arm64',
        'arm64': 'arm64',
        'armv7l': 'arm',
        'armv6l': 'arm'
    }
    arch = arch_map.get(machine, machine)

    if system == 'linux':
        os_part = 'linux'
    elif system == 'darwin':
        os_part = 'darwin'
    elif system == 'windows':
        os_part = 'windows'
    else:
        os_part = system  # fallback

    return f"{os_part}/{arch}"


class DockerBuilder:
    """Handles Docker image building using the Docker SDK for Python.

    Accepts parameters at call time so the same builder instance can run
    multiple sequential builds.
    """

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.client = self._initialize_client()

    def _initialize_client(self) -> Optional[docker.DockerClient]:
        """Initialize the Docker client."""
        self.logger.info("Connecting to Docker daemon...")
        client = docker.from_env()
        client.login(
            username=settings.docker_username,
            password=settings.docker_password,
            registry=settings.docker_registry
        )
        client.ping()
        self.logger.info("Successfully connected to Docker daemon.")
        return client

    def build_image(
            self,
            imageSettings: ImageSettings
    ) -> Optional[Image]:
        """Build a single Docker image.

        Returns:
            True if image build succeeded, False otherwise.
        """
        if not self.client:
            self.logger.error("Docker client not initialized. Aborting build.")
            return None

        self.logger.info("Starting Docker image build...")
        self.logger.info(f"Context: {imageSettings.workspace_path}")
        self.logger.info(f"Tag: {imageSettings.tag}")

        try:
            dockerfile = self._locate_dockerfile_in_settings(imageSettings)
            if dockerfile:
                # copy dockerfile found in settings location to workspace
                target_path = imageSettings.workspace_path / dockerfile.name
                shutil.copyfile(dockerfile, target_path)
            dockerfile = self._locate_dockerfile_in_workspace(imageSettings)

            workspace_path = imageSettings.workspace_path.resolve(strict=True)
            relative_dockerfile = dockerfile.relative_to(workspace_path)
            image, build_logs = self.client.images.build(
                path=str(workspace_path),
                dockerfile=str(relative_dockerfile),
                tag=imageSettings.tag,
                rm=True,
                buildargs={"TARGETPLATFORM": get_targetplatform()}
            )

            for chunk in build_logs:
                # Docker SDK may stream 'stream' or 'status' or other keys
                line = None
                if isinstance(chunk, dict):
                    if "stream" in chunk:
                        line = chunk["stream"].strip()
                    elif "status" in chunk:
                        # status messages (e.g., pulling, extracting)
                        status = chunk.get("status", "")
                        detail = chunk.get("progress", "")
                        line = f"{status} {detail}".strip()

                if line:
                    self.logger.info(line)

            self.logger.info(f"Image built successfully: {image.tags}")
            return image

        except BuildError as build_error:
            self.logger.error(f"Build failed: {build_error}")
            return None
        except APIError as api_error:
            self.logger.error(f"Docker API error: {api_error}")
            return None
        except Exception as error:
            self.logger.error(f"Unexpected error during build: {error}")
            return None

    @staticmethod
    def _locate_dockerfile_in_workspace(settings: ImageSettings) -> Optional[Path]:
        """Locate the Dockerfile in settings path or workspace path."""
        target_name = "Dockerfile"
        for path in settings.workspace_path.rglob(target_name):
            return path.resolve(strict=True)
        return None

    @staticmethod
    def _locate_dockerfile_in_settings(settings: ImageSettings) -> Optional[Path]:
        """Locate the Dockerfile in settings path or workspace path."""
        target_name = "Dockerfile"
        for path in settings.settings_file.parent.rglob(target_name):
            return path.resolve(strict=True)
        return None

    def push_image(self, imageSettings: ImageSettings) -> None:
        if not self.client:
            self.logger.error("Docker client not initialized. Aborting build.")
            return
        response = self.client.images.push(imageSettings.tag, stream=True, decode=True)
        prev_status = None
        for line in response:
            if 'status' in line and prev_status != line['status']:
                prev_status = line['status']
                self.logger.info(line['status'])
            elif 'errorDetail' in line:
                self.logger.error(line['errorDetail']['message'])
