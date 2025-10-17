import json
import os
import time
import subprocess
import hashlib
import platform
from datetime import datetime
from urllib.parse import urlparse

import git
import docker
from croniter import croniter

CONFIG_PATH = '/docker_builder_conf/config.json'
DOCKERFILES_DIR = '/dockerfiles'
REPOS_DIR = '/docker_image_builder/_repos'

# Global state
config = None
last_config_hash = None
docker_client = docker.from_env()

def load_config():
    """Load configuration from CONFIG_PATH."""
    global config, last_config_hash
    try:
        with open(CONFIG_PATH, 'r') as f:
            data = f.read()
        new_hash = hashlib.sha256(data.encode()).hexdigest()

        if new_hash == last_config_hash:
            return False  # No change detected

        config = json.loads(data)
        last_config_hash = new_hash
        print(f"[{datetime.now()}] Config loaded successfully.")
        return True
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[{datetime.now()}] Error loading config: {str(e)}")
        config = None
        last_config_hash = None
        return False

def ensure_dirs():
    """Ensure required directories exist."""
    os.makedirs(REPOS_DIR, exist_ok=True)

def safe_run(cmd):
    """Run a shell command safely, returning (success, output)."""
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, text=True)
        return True, output
    except subprocess.CalledProcessError as e:
        return False, e.output

def clone_or_pull_repo(container_cfg):
    """Clone or update the git repo."""
    repo_dir = os.path.join(REPOS_DIR, container_cfg['container_name'])
    url = container_cfg['github_url']
    branch = container_cfg.get('branch', 'main')
    token = container_cfg.get('github_token')

    if token:
        url = url.replace('https://', f'https://{token}@')

    try:
        if os.path.exists(repo_dir):
            repo = git.Repo(repo_dir)
            repo.git.fetch()
            repo.git.checkout(branch)
            repo.git.pull()
            print(f"[{datetime.now()}] Pulled repo {container_cfg['container_name']}.")
        else:
            git.Repo.clone_from(url, repo_dir, branch=branch)
            print(f"[{datetime.now()}] Cloned repo {container_cfg['container_name']}.")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] Git operation failed for {container_cfg['container_name']}: {str(e)}")
        return False

def get_targetplatform():
    system = platform.system().lower()   # 'linux', 'darwin', 'windows'
    machine = platform.machine().lower() # 'x86_64', 'arm64', 'aarch64', etc.

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
      
def build_image(container_cfg):
    """Build Docker image."""
    dockerfile_folder = os.path.join(DOCKERFILES_DIR, container_cfg['dockerfile'])
    if not os.path.exists(os.path.join(dockerfile_folder, 'Dockerfile')):
        print(f"[{datetime.now()}] Missing Dockerfile for {container_cfg['container_name']}.")
        return False

    context_dir = os.path.join(REPOS_DIR, container_cfg['container_name'])
    tag = f"{container_cfg['container_name']}:latest"

    try:
        image, _ = docker_client.images.build(
            path=context_dir,
            dockerfile=os.path.join(dockerfile_folder, 'Dockerfile'),
            tag=tag,
            rm=True,
            buildargs={"TARGETPLATFORM": get_targetplatform()}
        )
        print(f"[{datetime.now()}] Built image {tag} successfully.")
        return True
    except docker.errors.BuildError as e:
        print(f"[{datetime.now()}] Build failed for {container_cfg['container_name']}: {str(e)}")
        return False

def normalize_registry(registry: str) -> str:
    """
    Normalize the registry string by:
      - Removing any leading scheme (http:// or https://)
      - Stripping any trailing slashes
    """
    parsed = urlparse(registry)
    # If a scheme is present, use netloc + path; otherwise use the raw registry
    if parsed.scheme:
        host = parsed.netloc
        path = parsed.path.lstrip('/')
        registry_clean = f"{host}/{path}" if path else host
    else:
        registry_clean = registry

    # Remove any trailing slash
    return registry_clean.rstrip('/')

def push_image(container_cfg):
    """Push Docker image with a cleaned-up registry name."""
    name = container_cfg['container_name']
    tag = f"{name}:latest"

    # Normalize registry (strip protocol, extra slashes)
    raw_registry = container_cfg['docker_registry']
    registry = normalize_registry(raw_registry)

    full_tag = f"{registry}/{tag}"

    try:
        # Tag the image locally
        image = docker_client.images.get(tag)
        image.tag(full_tag)

        # Handle docker login if credentials provided
        username = container_cfg.get('docker_username')
        password = container_cfg.get('docker_password')
        if username and password:
            # Login against the registry hostname only
            registry_host = registry.split('/')[0]
            docker_client.login(username=username,
                                password=password,
                                registry=registry_host)

        # Push the cleaned-up reference
        response = docker_client.images.push(full_tag, stream=True, decode=True)
        for line in response:
            if 'errorDetail' in line:
                raise Exception(line['errorDetail']['message'])
        print(f"[{datetime.now()}] Pushed image {full_tag} successfully.")
        return True

    except Exception as e:
        print(f"[{datetime.now()}] Push failed for {name}: {str(e)}")
        return False

def main():
    """Main sequential supervisor loop with immediate first-run."""
    ensure_dirs()
    last_run_times = {}

    while True:
        config_changed = load_config()
        if config is None:
            time.sleep(5)
            continue

        now = datetime.now()

        if config_changed:
            # Clear all last-run markers so every container runs immediately
            last_run_times = {}

        for cfg in config.get('containers', []):
            name     = cfg['container_name']
            schedule = cfg.get('poll_interval', '* * * * *')

            # Determine if it's due:
            if name not in last_run_times:
                # First time (or after config change): build immediately
                due = True
            else:
                # Compute next scheduled time after the last run
                base = last_run_times[name]
                cron = croniter(schedule, base)
                next_run = cron.get_next(datetime)
                due = (now >= next_run)

            if due:
                print(f"[{now}] Building {name} (schedule: '{schedule}')…")
                try:
                    if clone_or_pull_repo(cfg):
                        if build_image(cfg):
                            push_image(cfg)
                except Exception as err:
                    print(f"[{datetime.now()}] Error processing {name}: {err}")
                # Mark this run’s time
                last_run_times[name] = now

        time.sleep(5)


if __name__ == "__main__":
    main()
