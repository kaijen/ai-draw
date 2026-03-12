# ai-draw

Batch AI image generation from YAML prompt files — consistent style, minimal cost.

Generate whiteboard-style stick-figure illustrations at scale using either the **Google Gemini API** or **OpenRouter** (100+ models including Flux, RiverFlow, and more). Every run is idempotent: already-generated files are skipped automatically.

## Features

- Two backends: `gemini-draw` (Gemini API) and `or-draw` (OpenRouter)
- YAML-driven batch generation — describe all images in one file
- Global or per-image reference images for style transfer
- Per-image overrides: model, temperature, aspect ratio
- Skip existing files — safe to re-run after failures
- Token + cost tracking (Gemini backend)
- Docker support with shell wrappers for Bash and PowerShell

## Installation

### pip (local development)

```bash
git clone https://github.com/youruser/ai-draw.git
cd ai-draw
pip install -e .
```

### Docker

```bash
docker build -t gemini-image-gen .
```

## Quick Start

1. Copy the example files and add your API keys:

```bash
cp .env.example .env
cp examples/prompts.yaml.sample prompts.yaml
```

2. Edit `prompts.yaml` with your image descriptions.

3. Run:

```bash
# Gemini backend
gemini-draw -f prompts.yaml -d output/

# OpenRouter backend
or-draw -f prompts.yaml -d output/
```

## CLI Reference

Both commands share the same options:

| Option | Short | Default | Description |
|---|---|---|---|
| `--api-key` | | env var | API key (`GEMINI_API_KEY` / `OPENROUTER_API_KEY`) |
| `--input-yaml` | `-f` | required | Path to prompts YAML file |
| `--global-ref` | `-r` | — | Reference image for style consistency |
| `--output-dir` | `-d` | `output` | Directory for generated images |
| `--global-temp` | `-t` | `0.3` | Default generation temperature |

## YAML Format

```yaml
images:
  - filename: "subfolder/image.png"   # output path relative to --output-dir
    prompt: "A stick figure climbing a mountain."
    temperature: 0.2                  # optional, overrides --global-temp
    aspect_ratio: "16:9"              # optional, default 16:9
    model: "google/gemini-2.0-flash-001"  # or-draw only
    reference_image: "ref/style.png"  # or-draw only, relative to YAML file
```

The `prompt` value can be a plain string or a path to a `.txt` file (resolved relative to the YAML file's directory).

See [`examples/prompts.yaml.sample`](examples/prompts.yaml.sample) for a full annotated example.

## Docker Usage

```bash
# Build once
docker compose build

# Gemini backend
docker compose run --rm gemini-draw -f prompts.yaml -d output/

# OpenRouter backend
docker compose run --rm or-draw -f prompts.yaml -d output/
```

Paths are always relative to the project root — no manual path translation needed.

## Shell Integration

Source the provided wrappers once so you can call `gemini-draw` and `or-draw` directly from any terminal, backed by Docker Compose:

- **Bash/Zsh**: [`examples/shell/.bashrc.sample`](examples/shell/.bashrc.sample)
- **PowerShell**: [`examples/shell/gemini-draw.ps1.sample`](examples/shell/gemini-draw.ps1.sample)

After setup:

```bash
gemini-draw -f prompts.yaml -r style_ref.png -d output/
or-draw     -f prompts.yaml -d output/
```

## Art Style

All images are generated with these enforced rules (defined in `src/ai_draw/common.py`):

- Minimalist stick-figure style with round heads
- Handdrawn whiteboard look with hatching (no gradients)
- Black & white with red as the only accent color
- 16:9 format at 1920×1080 px
- Absolutely no text or characters in the image
- Plain white background

## License

MIT
