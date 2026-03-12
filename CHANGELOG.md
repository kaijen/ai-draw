# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.1] - 2026-03-12

### Added
- Python package `ai-draw` installable via pip with `gemini-draw` and `or-draw` CLI entry points
- Gemini backend with direct Google API access and token cost tracking
- OpenRouter backend supporting 100+ models (Flux, RiverFlow, etc.)
- YAML-driven batch generation with per-image model, temperature, and aspect ratio control
- Idempotent runs — existing output files are skipped automatically
- Global and per-image reference image support for style consistency
- Docker Compose setup with separate services per backend, no path translation needed
- Shell wrappers for Bash/Zsh and PowerShell (docker compose-backed)
- hatch-vcs dynamic versioning from Git tags

[Unreleased]: https://github.com/kaijen/ai-draw/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/kaijen/ai-draw/releases/tag/v0.0.1
