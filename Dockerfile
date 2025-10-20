FROM docker:28.1.1

# 1) Install system deps
RUN apk add --no-cache \
      python3 \
      py3-pip \
      git \
      tzdata

# 2) Set workdir and copy in requirements
WORKDIR /docker_image_builder
COPY ./requirements.txt /docker_image_builder/.

# 3) Create a virtualenv and install deps into it
RUN python3 -m venv /venv \
 && /venv/bin/pip install --no-cache-dir -r /docker_image_builder/requirements.txt

# 4) Ensure the venv's python is used everywhere
ENV PATH="/venv/bin:$PATH"

# 5) Copy in your builder code
COPY docker_image_builder/ ./docker_image_builder/

# 6) Entrypoint: start Docker daemon silently, then run the script
ENTRYPOINT ["sh", "-c", "exec python3 -m docker_image_builder.main"]
