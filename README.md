created the entire app in one go.
it can now load a settings.yml file with 4 parameters:
schedule: '*/5 * * * *'
tag: ''
github_repo: ''
github_branch: 'master'

and create an image from that github repo. it will then push that image to the registry set by the environment variable "DOCKER_REGISTRY"

other environment variables that need to be set are:
DATA_DIR="/data"
SETTINGS_FILENAME="settings.yaml"
DOCKER_HOST="/var/run/docker.sock"
WORKING_DIR="/working_dir"
DOCKER_REGISTRY=""
DOCKER_USERNAME=""
DOCKER_PASSWORD=""

It is possible to create a custom dockerfile and place it in the config directory. The app will use that dockerfile instead of one from the github repo.
