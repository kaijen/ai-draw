# ai-draw

Batch AI image generation from YAML prompt files — consistent style, minimal cost.

Generate whiteboard-style stick-figure illustrations at scale using either the **Google Gemini API** or **OpenRouter** (FLUX, Stable Diffusion, and more). Every run is idempotent: already-generated files are skipped automatically.

## Features

- Two backends: `gemini-draw` (Gemini API) and `or-draw` (OpenRouter)
- YAML-driven batch generation — describe all images in one file
- Per-image overrides: model, temperature, aspect ratio, resolution
- Skip existing files — safe to re-run after failures
- Externalized system prompt — swap art styles without touching code
- Docker support with shell wrappers for Bash and PowerShell

## API Keys

### Gemini API Key (`GEMINI_API_KEY`)

> **Hinweis:** Ein Gemini-Abo (Google One mit Gemini Advanced) ist **nicht** dasselbe
> wie ein API-Zugang. Das Abo gilt fuer die consumer-App unter gemini.google.com.
> Die API wird separat ueber Google AI Studio abgerechnet.

1. Gehe zu **[Google AI Studio](https://aistudio.google.com/)**
2. Melde dich mit deinem Google-Konto an (dasselbe wie dein Gemini-Abo)
3. Klicke links auf **"Get API key"**
4. Waehle **"Create API key"** (bestehendes Google Cloud Projekt oder neues anlegen)
5. Kopiere den Key und trage ihn in `.env` ein:

```
GEMINI_API_KEY=AIza...
```

**Abrechnung:** Es gibt ein kostenloses Kontingent mit Rate-Limits. Darueber hinaus
wird pay-as-you-go ueber Google Cloud abgerechnet.

### OpenRouter API Key (`OPENROUTER_API_KEY`)

1. Registriere dich unter **[openrouter.ai](https://openrouter.ai/)**
2. Gehe zu **Keys** im Dashboard und klicke **"Create Key"**
3. Kopiere den Key und trage ihn in `.env` ein:

```
OPENROUTER_API_KEY=sk-or-...
```

OpenRouter ist pay-as-you-go ohne monatliches Abo.

## Installation

### pip (local development)

```bash
git clone https://github.com/kaijen/ai-draw.git
cd ai-draw
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Docker

See [Docker Usage](#docker-usage) below.

## Quick Start

1. Copy the example files and add your API keys:

```bash
mkdir workspace && cp examples/.env.example workspace/.env
cp examples/prompts.yaml.sample workspace/prompts.yaml
# Edit workspace/.env with your keys
```

2. Edit `workspace/prompts.yaml` with your image descriptions.

3. Run from the `workspace/` directory:

```bash
cd workspace

# Gemini backend
gemini-draw -f prompts.yaml -d output/

# OpenRouter backend (FLUX, 1920x1080)
or-draw -f prompts.yaml -d output/
```

## CLI Reference

### gemini-draw

| Option | Short | Default | Env var | Description |
|---|---|---|---|---|
| `--api-key` | | required | `GEMINI_API_KEY` | Gemini API key |
| `--input-yaml` | `-f` | required | | Path to prompts YAML file |
| `--output-dir` | `-d` | `output` | | Directory for generated images |
| `--global-temp` | `-t` | `0.3` | | Default generation temperature |
| `--model` | `-m` | `gemini-2.5-flash-preview-04-17` | `GEMINI_MODEL` | Model name |
| `--aspect-ratio` | `-a` | `16:9` | | Aspect ratio hint (text prompt) |
| `--system-prompt-file` | `-p` | | `GEMINI_SYSTEM_PROMPT_FILE` | Custom system prompt file |

### or-draw

| Option | Short | Default | Env var | Description |
|---|---|---|---|---|
| `--api-key` | | required | `OPENROUTER_API_KEY` | OpenRouter API key |
| `--input-yaml` | `-f` | required | | Path to prompts YAML file |
| `--output-dir` | `-d` | `output` | | Directory for generated images |
| `--global-temp` | `-t` | `0.3` | | Default generation temperature |
| `--model` | `-m` | `black-forest-labs/flux.2-pro` | `OR_MODEL` | Model ID |
| `--width` | `-W` | `1920` | | Output image width in pixels |
| `--height` | `-H` | `1080` | | Output image height in pixels |
| `--system-prompt-file` | `-p` | | `OR_SYSTEM_PROMPT_FILE` | Custom system prompt file |

## YAML Format

```yaml
images:
  - filename: "subfolder/image.png"   # output path relative to --output-dir
    prompt: "A stick figure climbing a mountain."
    temperature: 0.2                  # optional, overrides --global-temp

    # gemini-draw options
    aspect_ratio: "16:9"              # optional, text hint to model

    # or-draw options
    model: "black-forest-labs/flux.2-pro"     # optional, overrides --model
    width: 1920                       # optional, overrides --width
    height: 1080                      # optional, overrides --height
```

See [`examples/prompts.yaml.sample`](examples/prompts.yaml.sample) for a full annotated example.

## Art Style

The built-in system prompt (`src/ai_draw/common.py`, also at `examples/SYSTEM_PROMPT.md`) enforces:

- Minimalist stick-figure style with round heads
- Handdrawn whiteboard look with hatching (no gradients)
- Black & white with red as the only accent color
- Absolutely no text or characters in the image
- Plain white background

Override for any run:

```bash
gemini-draw -f prompts.yaml -p examples/SYSTEM_PROMPT.md -d output/
or-draw     -f prompts.yaml -p my_style.md -d output/
```

Or set persistently via `.env`:

```
GEMINI_SYSTEM_PROMPT_FILE=examples/SYSTEM_PROMPT.md
OR_SYSTEM_PROMPT_FILE=examples/SYSTEM_PROMPT.md
```

## Docker Usage

The image is hosted on [GitHub Container Registry](https://github.com/kaijen/ai-draw/pkgs/container/ai-draw).

```bash
# Pull and run Gemini backend
docker compose -f docker/docker-compose.yml run --rm gemini-draw -f prompts.yaml -d output/

# Pull and run OpenRouter backend
docker compose -f docker/docker-compose.yml run --rm or-draw -f prompts.yaml -d output/
```

Or use the [justfile](justfile):

```bash
just gemini-draw -f prompts.yaml -d output/
just or-draw     -f prompts.yaml -d output/
```

Paths are always relative to the project root — no manual path translation needed.

## Building & Publishing

```bash
just build    # Build Docker image locally
just push     # Push :latest to ghcr.io (requires GITHUB_TOKEN)
just release  # Tag current git version and push :VERSION + :latest
```

## Shell Integration

Source the provided wrappers once so you can call `gemini-draw` and `or-draw` directly from any terminal, backed by Docker Compose:

- **Bash/Zsh**: [`examples/shell/.bashrc.sample`](examples/shell/.bashrc.sample)
- **PowerShell**: [`examples/shell/gemini-draw.ps1.sample`](examples/shell/gemini-draw.ps1.sample)

## License

MIT
