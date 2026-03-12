image  := "ghcr.io/kaijen/ai-draw"
tag    := `git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "dev"`
compose := "docker compose -f docker/docker-compose.yml"

# Show available recipes
default:
    @just --list

# Login to GitHub Container Registry (requires GITHUB_TOKEN env var)
login:
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u kaijen --password-stdin

# Build Docker image locally
build:
    {{compose}} build

# Push :latest to ghcr.io
push: build
    docker push {{image}}:latest

# Tag current git version, push :VERSION and :latest
release: build
    docker tag {{image}}:latest {{image}}:{{tag}}
    docker push {{image}}:{{tag}}
    docker push {{image}}:latest
    @echo "Released {{image}}:{{tag}}"

# Run gemini-draw via Docker
gemini-draw *ARGS:
    {{compose}} run --rm gemini-draw {{ARGS}}

# Run or-draw via Docker
or-draw *ARGS:
    {{compose}} run --rm or-draw {{ARGS}}
