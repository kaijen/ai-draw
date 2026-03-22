FROM python:3.13-slim

WORKDIR /app

# System dependencies for Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the package (includes both gemini-draw and replicate-draw CLI commands).
# Build context is the project root (see docker-compose.yml).
# VERSION is passed as a build arg so hatch-vcs can resolve the version without
# a .git directory being present in the build context.
ARG VERSION=dev
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Mount point for project files — bound via docker-compose volume
RUN mkdir /app/data
