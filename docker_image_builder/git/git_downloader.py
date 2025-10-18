from git import Repo, GitCommandError

from docker_image_builder.logger import get_logger
from docker_image_builder.settings import settings
from docker_image_builder.workspace.image_settings import ImageSettings

logger = get_logger(__name__)


def prepare_repo(imageSettings: ImageSettings) -> None:
    """Clone or update the Git repository"""
    repo_url = imageSettings.github_repo
    branch = imageSettings.github_branch
    workspace = imageSettings.workspace_path

    logger.info(f"Cloning repository {repo_url}")
    if not repo_url:
        raise ValueError("github_repo is not set in ImageSettings")

    if not settings.working_dir.exists():
        settings.working_dir.mkdir(parents=True)

    if workspace.exists():
        try:
            repo = Repo(workspace)
            repo.git.checkout(branch)
            repo.remotes.origin.pull()
        except GitCommandError as e:
            logger.error(e)
            raise e
    else:
        try:
            Repo.clone_from(repo_url, workspace, branch=branch)
        except GitCommandError as e:
            logger.error(e)
            raise e
