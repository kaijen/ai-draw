# CLAUDE.md — Developer Guide

## Project Overview

`ai-draw` is a Python package providing two CLI tools for scripted AI image generation:

- **`gemini-draw`** — uses the Google Gemini API (`generate_content` with `response_modalities=["IMAGE","TEXT"]`)
- **`replicate-draw`** — uses the Replicate API (FLUX and other models)

All tools read a YAML file describing a batch of images and skip already-generated files (idempotent).

## Setup

### Install for development

```bash
pip install -e .
```

This installs all CLI entry points (`gemini-draw`, `replicate-draw`) pointing at the source in `src/`.

### Environment variables

Copy `examples/.env.example` to `.env` and fill in your API keys. The tools auto-load `.env` from the current working directory (python-dotenv, `usecwd=True`).

| Variable | Used by | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | `gemini-draw` | required |
| `GEMINI_MODEL` | `gemini-draw` | override default model |
| `GEMINI_SYSTEM_PROMPT_FILE` | `gemini-draw` | path to custom system prompt |
| `GEMINI_REFERENCE_IMAGES` | `gemini-draw` | comma-separated global reference image paths |
| `REPLICATE_API_TOKEN` | `replicate-draw`, `gemini-draw` (upscaler) | required |
| `REPLICATE_MODEL` | `replicate-draw` | override default model |
| `REPLICATE_UPSCALER_MODEL` | both | override default upscaler model |
| `REPLICATE_SYSTEM_PROMPT_FILE` | `replicate-draw` | path to custom system prompt |
| `REPLICATE_REFERENCE_IMAGES` | `replicate-draw` | comma-separated global reference image paths |
| `REPLICATE_GUIDANCE_SCALE` | `replicate-draw` | default guidance scale |
| `REPLICATE_NEGATIVE_PROMPT` | `replicate-draw` | default negative prompt |

## Running the CLIs

```bash
gemini-draw    -f prompts.yaml -d output/
replicate-draw -f prompts.yaml -d output/
```

Full option reference:

```
gemini-draw --help
replicate-draw --help
```

## Project Layout

```
src/ai_draw/
  common.py       — SYSTEM_RULES, clean_multiline_string(), safe_makedirs()
  gemini.py       — Gemini backend + CLI entry point
  replicate.py    — Replicate backend + CLI entry point
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
| `REPLICATE_MODEL` | `replicate.py` | Default Replicate model ID |
| `REPLICATE_UPSCALER_MODEL` | `common.py` | Default upscaler model ID (shared) |
| `PRICE_PER_IMAGE` | `replicate.py` | Per-image generation cost estimate |
| `PRICE_PER_UPSCALE` | `common.py` | Per-image upscale cost estimate (shared) |
| `SYSTEM_RULES` | `common.py` | Shared drawing-style instructions |

## Backend Details

### gemini-draw

- Uses `client.models.generate_content()` with `response_modalities=["IMAGE", "TEXT"]`
- System prompt passed via `GenerateContentConfig.system_instruction`
- Output resolution is fixed by the model (~1360×768 for most Gemini image models)
- `--aspect-ratio` is a text hint to the model, not an API parameter
- **Upscaling pipeline**: same as replicate-draw; requires `REPLICATE_API_TOKEN` in env
- **`allow_text`**: per-image YAML key; when `true`, replaces the hardcoded "no text/symbols" constraint with an explicit allowance — use for images that require mathematical symbols or labels
- Per-image `aspect_ratio`, `width`, `height`, `upscaler_model`, `reference_images`, `temperature`, and `allow_text` keys in YAML extend/override CLI defaults

### replicate-draw

- Uses `replicate.Client.run()` with the model ID and `prompt`, `aspect_ratio`, `output_format` as inputs
- System prompt prepended to the user prompt
- Default model: `black-forest-labs/flux-2-pro`; optimized for FLUX models
- `--aspect-ratio` is passed directly to the model (e.g. `16:9`, `9:16`, `1:1`)
- **Upscaling pipeline**: when `--width` and/or `--height` are set and the generated image is smaller, an upscaler model is called automatically. Scale factor = `ceil(max(target_w/actual_w, target_h/actual_h))`. The upscaler receives `image` (file) and `scale` (integer) — compatible with `nightmareai/real-esrgan` and similar models. Implemented in `common.py` (`run_upscale`), shared with `gemini-draw`.
- Default upscaler: `nightmareai/real-esrgan`
- **Reference images**: global defaults via `--reference-images` / `REPLICATE_REFERENCE_IMAGES` (comma-separated paths); per-image `reference_images` in YAML are merged (appended) on top. Passed as both `input_images` (Flux) and `reference_images` (SeedDream) to maximise model compatibility.
- **`guidance_scale`**: per-image or CLI (`-g`); supported by SeedDream and similar models (range 1–10)
- **`negative_prompt`**: per-image or CLI (`-n`); supported by SeedDream and similar models
- Per-image `model`, `aspect_ratio`, `width`, `height`, `upscaler_model`, `reference_images`, `guidance_scale`, and `negative_prompt` keys in YAML extend/override CLI defaults

## Docker

```bash
# Build image locally
just build

# Push :latest to ghcr.io (requires GITHUB_TOKEN)
just push

# Release current git tag to ghcr.io
just release

# Run backends
just gemini-draw    -f prompts.yaml -d output/
just replicate-draw -f prompts.yaml -d output/
```

Paths are relative to the project root — no manual path translation needed.

## Code Conventions

- Use `safe_makedirs(output_path)` instead of `os.makedirs(os.path.dirname(...))` directly — the latter crashes when `output_path` has no directory component.
- All Click options must have `--help` text.
- Keep user-facing strings in English.
