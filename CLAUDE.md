# CLAUDE.md — Developer Guide

## Project Overview

`ai-draw` is a Python package providing two CLI tools for scripted AI image generation:

- **`gemini-draw`** — uses the Google Gemini API (`generate_content` with `response_modalities=["IMAGE","TEXT"]`)
- **`or-draw`** — uses the OpenRouter `/images/generations` endpoint (FLUX, Stable Diffusion, etc.)

Both tools read a YAML file describing a batch of images and skip already-generated files (idempotent).

## Setup

### Install for development

```bash
pip install -e .
```

This installs both CLI entry points (`gemini-draw`, `or-draw`) pointing at the source in `src/`.

### Environment variables

Copy `examples/.env.example` to `.env` and fill in your API keys. The tools auto-load `.env` from the current working directory (python-dotenv, `usecwd=True`).

| Variable | Used by | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | `gemini-draw` | required |
| `GEMINI_MODEL` | `gemini-draw` | override default model |
| `GEMINI_SYSTEM_PROMPT_FILE` | `gemini-draw` | path to custom system prompt |
| `OPENROUTER_API_KEY` | `or-draw` | required |
| `OR_MODEL` | `or-draw` | override default model |
| `OR_SYSTEM_PROMPT_FILE` | `or-draw` | path to custom system prompt |

## Running the CLIs

```bash
gemini-draw -f prompts.yaml -d output/
or-draw     -f prompts.yaml -d output/
```

Full option reference:

```
gemini-draw --help
or-draw --help
```

## Project Layout

```
src/ai_draw/
  common.py       — SYSTEM_RULES, clean_multiline_string(), safe_makedirs()
  gemini.py       — Gemini backend + CLI entry point
  openrouter.py   — OpenRouter backend + CLI entry point
docker/
  Dockerfile          — image build definition (context: project root)
  docker-compose.yml  — defines gemini-draw and or-draw services (uses ghcr.io image)
examples/
  .env.example            — copy to workspace/.env and fill in keys
  SYSTEM_PROMPT.md        — default system prompt (overridable via -p)
  prompts.yaml.sample     — annotated YAML schema reference
  shell/
    .bashrc.sample         — Bash wrapper (sources docker compose)
    gemini-draw.ps1.sample — PowerShell wrapper (sources docker compose)
justfile  — recipes: build, push, release, gemini-draw, or-draw
```

## Key Constants

| Constant | File | Purpose |
|---|---|---|
| `GEMINI_MODEL` | `gemini.py` | Default Gemini model ID |
| `PRICE_PER_IMAGE` | `gemini.py` | Flat per-image fee for cost estimate |
| `OR_MODEL` | `openrouter.py` | Default OpenRouter model ID |
| `SYSTEM_RULES` | `common.py` | Shared drawing-style instructions |

## Backend Details

### gemini-draw

- Uses `client.models.generate_content()` with `response_modalities=["IMAGE", "TEXT"]`
- System prompt passed via `GenerateContentConfig.system_instruction`
- Output resolution is fixed by the model (~1360×768 for most Gemini image models)
- `--aspect-ratio` is a text hint to the model, not an API parameter

### or-draw

- Uses `POST /api/v1/chat/completions` with `width`/`height` as extra body params
- System prompt prepended to prompt text
- `--width` / `--height` default to 1920×1080; passed directly in the payload
- Per-image `width` / `height` keys in YAML override the CLI defaults
- Optimized for FLUX models; other models may ignore width/height

## Docker

```bash
# Build image locally
just build

# Push :latest to ghcr.io (requires GITHUB_TOKEN)
just push

# Release current git tag to ghcr.io
just release

# Run backends
just gemini-draw -f prompts.yaml -d output/
just or-draw     -f prompts.yaml -d output/
```

Paths are relative to the project root — no manual path translation needed.

## Code Conventions

- Use `safe_makedirs(output_path)` instead of `os.makedirs(os.path.dirname(...))` directly — the latter crashes when `output_path` has no directory component.
- All Click options must have `--help` text.
- Keep user-facing strings in English.
