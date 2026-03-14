# ai-draw

Batch AI image generation from YAML prompt files — consistent style, minimal cost.

Generate whiteboard-style stick-figure illustrations at scale using either the **Google Gemini API** or the **Replicate API** (FLUX and more). Every run is idempotent: already-generated files are skipped automatically.

## Features

- Two backends: `gemini-draw` (Gemini API) and `replicate-draw` (Replicate API)
- YAML-driven batch generation — describe all images in one file
- Per-image overrides: model, aspect ratio, target resolution
- Skip existing files — safe to re-run after failures
- Automatic upscaling: `replicate-draw` detects low-resolution output and upscales to the target resolution via a configurable upscaler model
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

### Replicate API Token (`REPLICATE_API_TOKEN`)

1. Registriere dich unter **[replicate.com](https://replicate.com/)**
2. Gehe zu **Account → API tokens** und klicke **"Create token"**
3. Kopiere den Token und trage ihn in `.env` ein:

```
REPLICATE_API_TOKEN=r8_...
```

Replicate ist pay-as-you-go ohne monatliches Abo.

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

# Replicate backend (FLUX 2 Pro, upscale to 1920x1080 if needed)
replicate-draw -f prompts.yaml -d output/ --width 1920 --height 1080
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
| `--reference-images` | `-R` | | | Global reference images for style (repeatable) |
| `--system-prompt-file` | `-p` | | `GEMINI_SYSTEM_PROMPT_FILE` | Custom system prompt file |

### replicate-draw

| Option | Short | Default | Env var | Description |
|---|---|---|---|---|
| `--api-key` | | required | `REPLICATE_API_TOKEN` | Replicate API token |
| `--input-yaml` | `-f` | required | | Path to prompts YAML file |
| `--output-dir` | `-d` | `output` | | Directory for generated images |
| `--model` | `-m` | `black-forest-labs/flux-2-pro` | `REPLICATE_MODEL` | Model ID |
| `--aspect-ratio` | `-a` | `16:9` | | Output aspect ratio |
| `--width` | `-W` | | | Target width in pixels — triggers upscaling if image is smaller |
| `--height` | `-H` | | | Target height in pixels — triggers upscaling if image is smaller |
| `--upscaler-model` | `-u` | `nightmareai/real-esrgan` | `REPLICATE_UPSCALER_MODEL` | Upscaler model ID |
| `--system-prompt-file` | `-p` | | `REPLICATE_SYSTEM_PROMPT_FILE` | Custom system prompt file |

## YAML Format

```yaml
images:
  - filename: "subfolder/image.png"   # output path relative to --output-dir
    prompt: "A stick figure climbing a mountain."
    aspect_ratio: "16:9"              # optional, overrides --aspect-ratio

    # gemini-draw options
    temperature: 0.2                  # optional, overrides --global-temp
    reference_images:                 # optional, paths relative to the YAML file
      - "ref/style.png"

    # replicate-draw options
    model: "black-forest-labs/flux-2-pro"  # optional, overrides --model
    width: 1920                       # optional, target width for upscaling
    height: 1080                      # optional, target height for upscaling
    upscaler_model: "nightmareai/real-esrgan"  # optional, overrides --upscaler-model
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
gemini-draw    -f prompts.yaml -p examples/SYSTEM_PROMPT.md -d output/
replicate-draw -f prompts.yaml -p my_style.md -d output/
```

Or set persistently via `.env`:

```
GEMINI_SYSTEM_PROMPT_FILE=examples/SYSTEM_PROMPT.md
REPLICATE_SYSTEM_PROMPT_FILE=examples/SYSTEM_PROMPT.md
```

## Docker Usage

The image is hosted on [GitHub Container Registry](https://github.com/kaijen/ai-draw/pkgs/container/ai-draw).

```bash
# Pull and run Gemini backend
docker compose -f docker/docker-compose.yml run --rm gemini-draw -f prompts.yaml -d output/

# Pull and run Replicate backend
docker compose -f docker/docker-compose.yml run --rm replicate-draw -f prompts.yaml -d output/
```

Or use the [justfile](justfile):

```bash
just gemini-draw    -f prompts.yaml -d output/
just replicate-draw -f prompts.yaml -d output/
```

Paths are always relative to the project root — no manual path translation needed.

## Building & Publishing

```bash
just build    # Build Docker image locally
just push     # Push :latest to ghcr.io (requires GITHUB_TOKEN)
just release  # Tag current git version and push :VERSION + :latest
```

## Shell Integration

Source the provided wrappers once so you can call `gemini-draw` and `replicate-draw` directly from any terminal, backed by Docker Compose:

- **Bash/Zsh**: [`examples/shell/.bashrc.sample`](examples/shell/.bashrc.sample)
- **PowerShell**: [`examples/shell/gemini-draw.ps1.sample`](examples/shell/gemini-draw.ps1.sample)

## License

MIT
