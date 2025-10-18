from docker_image_builder.docker.builder import DockerBuilder
from docker_image_builder.git.git_downloader import prepare_repo
from docker_image_builder.workspace.image_settings import ImageSettings


class ImageBuilder:
    def __init__(self, imageSettings: ImageSettings) -> None:
        self.settings = imageSettings

    def build(self):
        self.settings.refresh()
        self._update_contents()
        docker_builder = DockerBuilder()
        image = docker_builder.build_image(self.settings)
        if image:
            docker_builder.push_image(self.settings)

    def _update_contents(self):
        prepare_repo(self.settings)
