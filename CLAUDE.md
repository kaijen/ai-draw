# CLAUDE.md — Developer Guide

## Project Overview

`ai-draw` is a Python package providing a CLI tool for scripted AI image generation:

- **`gemini-draw`** — uses the Google Gemini API (`generate_content` with `response_modalities=["IMAGE","TEXT"]`), with optional upscaling via Replicate Real-ESRGAN

The tool reads a YAML file describing a batch of images and skips already-generated files (idempotent).

## Setup

### Install for development

```bash
pip install -e .
```

This installs the `gemini-draw` CLI entry point pointing at the source in `src/`.

### Environment variables

Copy `examples/.env.example` to `.env` and fill in your API keys. The tool auto-loads `.env` from the current working directory (python-dotenv, `usecwd=True`).

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | required |
| `GEMINI_MODEL` | override default model |
| `GEMINI_SYSTEM_PROMPT_FILE` | path to custom system prompt |
| `REPLICATE_API_KEY` | required when `--upscale` is used |

## Running the CLI

```bash
gemini-draw -f prompts.yaml -d output/
```

Full option reference:

```
gemini-draw --help
```

## Project Layout

```
src/ai_draw/
  common.py       — SYSTEM_RULES, clean_multiline_string(), safe_makedirs()
  gemini.py       — Gemini backend + CLI entry point
docker/
  Dockerfile          — image build definition (context: project root)
  docker-compose.yml  — defines the gemini-draw service (uses ghcr.io image)
examples/
  .env.example            — copy to workspace/.env and fill in keys
  SYSTEM_PROMPT.md        — default system prompt (overridable via -p)
  prompts.yaml.sample     — annotated YAML schema reference
  shell/
    .bashrc.sample         — Bash wrapper (sources docker compose)
    gemini-draw.ps1.sample — PowerShell wrapper (sources docker compose)
justfile  — recipes: build, push, release, gemini-draw
```

## Key Constants

| Constant | File | Purpose |
|---|---|---|
| `GEMINI_MODEL` | `gemini.py` | Default Gemini model ID |
| `PRICE_PER_IMAGE` | `gemini.py` | Flat per-image fee for cost estimate |
| `SYSTEM_RULES` | `common.py` | Shared drawing-style instructions |

## Backend Details

### gemini-draw

- Uses `client.models.generate_content()` with `response_modalities=["IMAGE", "TEXT"]`
- System prompt passed via `GenerateContentConfig.system_instruction`
- Output resolution is fixed by the model (~1360×768 for most Gemini image models)
- `--aspect-ratio` is a text hint to the model, not an API parameter
- `--upscale` optionally upscales each generated image via **Replicate Real-ESRGAN** (`nightmareai/real-esrgan`):
  1. Calls `replicate.Client.run()` with the image file (4× scale); the SDK handles upload and polling
  2. Resizes the result to the target resolution using Pillow LANCZOS and overwrites the file in-place
- Target resolution priority (highest wins): YAML `resolution: "WxH"` > YAML `width`/`height` > CLI `--width`/`--height` (default 1920×1080)
- Requires `REPLICATE_API_KEY` in `.env` (or `--replicate-api-key` flag) when `--upscale` is active

## Docker

```bash
# Build image locally
just build

# Push :latest to ghcr.io (requires GITHUB_TOKEN)
just push

# Release current git tag to ghcr.io
just release

# Run backend
just gemini-draw -f prompts.yaml -d output/
```

Paths are relative to the project root — no manual path translation needed.

## Code Conventions

- Use `safe_makedirs(output_path)` instead of `os.makedirs(os.path.dirname(...))` directly — the latter crashes when `output_path` has no directory component.
- All Click options must have `--help` text.
- Keep user-facing strings in English.
