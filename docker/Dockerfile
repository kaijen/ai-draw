FROM python:3.11-slim

WORKDIR /app

# System dependencies for Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install the package (includes both gemini-draw and or-draw CLI commands).
# Build context is the project root (see docker-compose.yml).
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Mount point for project files — bound via docker-compose volume
RUN mkdir /app/data
