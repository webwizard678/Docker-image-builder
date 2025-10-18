from pathlib import Path
from git import Repo, GitCommandError

from docker_image_builder.logger import get_logger
from docker_image_builder.workspace.image_settings import ImageSettings

logger = get_logger(__name__)


def prepare_repo(imageSettings: ImageSettings) -> None:
    """Clone or update the Git repository"""
    return
    repo_url = imageSettings.github_repo
    branch = imageSettings.github_branch
    workspace = imageSettings.workspace_path

    logger.info(f"Cloning repository {repo_url}")
    if not repo_url:
        raise ValueError("github_repo is not set in ImageSettings")

    if not workspace.exists():
        workspace.mkdir(parents=True)

    repo_path = workspace / Path(repo_url).stem

    if repo_path.exists():
        try:
            repo = Repo(repo_path)
            repo.git.checkout(branch)
            repo.remotes.origin.pull()
        except GitCommandError as e:
            raise RuntimeError(f"Failed to update repository: {e}")
    else:
        try:
            Repo.clone_from(repo_url, repo_path, branch=branch)
        except GitCommandError as e:
            raise RuntimeError(f"Failed to clone repository: {e}")
