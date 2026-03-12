# CLAUDE.md — Developer Guide

## Project Overview

`ai-draw` is a Python package providing two CLI tools for scripted AI image generation:

- **`gemini-draw`** — uses the Google Gemini API directly (with token cost tracking)
- **`or-draw`** — uses OpenRouter to access many models (Gemini, Flux, RiverFlow, etc.)

Both tools read a YAML file describing a batch of images, skip already-generated files (idempotent), and support a global reference image for style consistency.

## Setup

### Install for development

```bash
pip install -e .
```

This installs both CLI entry points (`gemini-draw`, `or-draw`) pointing at the source in `src/`.

### Environment variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

| Variable | Used by |
|---|---|
| `GEMINI_API_KEY` | `gemini-draw` |
| `OPENROUTER_API_KEY` | `or-draw` |

## Running the CLIs

```bash
gemini-draw -f examples/prompts.yaml.sample -d output/
or-draw     -f examples/prompts.yaml.sample -d output/
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
  Dockerfile      — image build definition (context: project root)
examples/
  prompts.yaml.sample     — annotated YAML schema reference
  shell/
    .bashrc.sample         — Bash wrapper (sources docker compose)
    gemini-draw.ps1.sample — PowerShell wrapper (sources docker compose)
docker-compose.yml  — defines gemini-draw and or-draw services
```

## Key Constants

| Constant | File | Purpose |
|---|---|---|
| `GEMINI_MODEL` | `gemini.py` | Model ID — update when the Gemini image model name changes |
| `PRICE_PER_1M_INPUT/OUTPUT` | `gemini.py` | Update for current Gemini pricing |
| `PRICE_PER_IMAGE` | `gemini.py` | Flat per-image fee added to cost estimate |
| `SYSTEM_RULES` | `common.py` | Shared drawing-style instructions sent to all models |

## Docker

```bash
# Build
docker compose build

# Run Gemini backend
docker compose run --rm gemini-draw -f prompts.yaml -d output/

# Run OpenRouter backend
docker compose run --rm or-draw -f prompts.yaml -d output/
```

Paths are relative to the project root — no manual path translation needed.

## Code Conventions

- Use `safe_makedirs(output_path)` instead of `os.makedirs(os.path.dirname(...))` directly — the latter crashes when `output_path` has no directory component.
- All Click options must have `--help` text.
- Keep user-facing strings in English.
