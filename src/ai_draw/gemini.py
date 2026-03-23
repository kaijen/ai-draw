import os

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import click
import yaml
from google import genai
from google.genai import types

from ai_draw.common import (
    SYSTEM_RULES, REPLICATE_UPSCALER_MODEL,
    clean_multiline_string, safe_makedirs, run_upscale,
)

PRICE_PER_IMAGE = 0.003

GEMINI_MODEL = "gemini-2.5-flash-preview-04-17"


_SNIPPET = 12  # bytes to show at each end of a binary blob


def _image_part(path: str) -> types.Part:
    with open(path, "rb") as f:
        data = f.read()
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return types.Part.from_bytes(data=data, mime_type=mime)


def _blob_repr(data: bytes) -> str:
    """Return a short human-readable snippet of binary data."""
    n = len(data)
    if n <= _SNIPPET * 2:
        return data.hex()
    return f"{data[:_SNIPPET].hex()} ... {data[-_SNIPPET:].hex()} ({n} bytes)"


def _debug_part(part, label: str) -> None:
    if hasattr(part, "text") and part.text is not None:
        click.secho(f"    {label} text: {part.text!r}", fg="magenta")
    elif hasattr(part, "inline_data") and part.inline_data:
        blob = _blob_repr(part.inline_data.data)
        click.secho(f"    {label} image ({part.inline_data.mime_type}): {blob}", fg="magenta")
    else:
        click.secho(f"    {label}: {part!r}", fg="magenta")


def _debug_contents(contents: list, system_instruction: str) -> None:
    click.secho("\n── DEBUG REQUEST ─────────────────────────────────", fg="magenta")
    click.secho(f"  system_instruction: {system_instruction!r}", fg="magenta")
    for cidx, content in enumerate(contents):
        role = getattr(content, "role", "?")
        parts = getattr(content, "parts", [content])
        click.secho(f"  contents[{cidx}] role={role!r} ({len(parts)} part(s)):", fg="magenta")
        for pidx, part in enumerate(parts):
            _debug_part(part, f"part[{pidx}]")
    click.secho("──────────────────────────────────────────────────\n", fg="magenta")


def _debug_response(response) -> None:
    click.secho("\n── DEBUG RESPONSE ────────────────────────────────", fg="cyan")
    if not response.candidates:
        click.secho("  (no candidates)", fg="cyan")
        click.secho("─────────────────────────────────────────────────\n", fg="cyan")
        return
    for cidx, candidate in enumerate(response.candidates):
        click.secho(f"  candidate[{cidx}] finish_reason={candidate.finish_reason}", fg="cyan")
        for pidx, part in enumerate(candidate.content.parts):
            if hasattr(part, "inline_data") and part.inline_data:
                blob = _blob_repr(part.inline_data.data)
                click.secho(
                    f"    part[{pidx}] image ({part.inline_data.mime_type}): {blob}",
                    fg="cyan",
                )
            elif hasattr(part, "text") and part.text:
                click.secho(f"    part[{pidx}] text: {part.text!r}", fg="cyan")
            else:
                click.secho(f"    part[{pidx}]: {part!r}", fg="cyan")
    click.secho("─────────────────────────────────────────────────\n", fg="cyan")


def run_generation(client, model_name, system_instruction, prompt, output_path,
                   reference_images: list[str] | None = None,
                   aspect_ratio: str = "16:9", temp: float = 0.3,
                   allow_text: bool = False, debug: bool = False):
    if os.path.exists(output_path):
        click.secho(f"   Skipping: {os.path.basename(output_path)}", fg="yellow")
        return 0.0

    safe_makedirs(output_path)

    parts: list = []
    for ref_path in (reference_images or []):
        if os.path.exists(ref_path):
            parts.append(_image_part(ref_path))
        else:
            click.secho(f"   Warning: reference image not found: {ref_path}", fg="yellow")

    # Embed hard constraints directly in the user turn so the model cannot ignore them
    text_rule = (
        "2. Symbols, mathematical operators, and labels ARE allowed and required as described."
        if allow_text else
        "2. ABSOLUTELY NO text, letters, digits, symbols, or writing of any kind in the image."
    )
    user_text = (
        f"STRICT REQUIREMENTS — violating any of these invalidates the image:\n"
        f"1. Output aspect ratio: {aspect_ratio} (exact, no cropping).\n"
        f"{text_rule}\n\n"
        f"Subject: {clean_multiline_string(prompt)}"
    )
    parts.append(types.Part.from_text(text=user_text))

    # All parts must be in a single Content so the model sees them as one user turn
    contents = [types.Content(role="user", parts=parts)]

    if debug:
        _debug_contents(contents, system_instruction)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,  # preserve newlines for readability
                temperature=temp,
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        if debug:
            _debug_response(response)
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)
                    return PRICE_PER_IMAGE
    except Exception as e:
        click.secho(f"   Error: {e}", fg="red")
    return 0.0


@click.command()
@click.option("--api-key", envvar="GEMINI_API_KEY", required=True, help="Gemini API key.")
@click.option("--input-yaml", "-f", type=click.Path(exists=True), required=True, help="Path to prompts YAML file.")
@click.option("--output-dir", "-d", default="output", show_default=True, help="Output directory for generated images.")
@click.option("--global-temp", "-t", type=float, default=0.3, show_default=True, help="Default generation temperature.")
@click.option("--model", "-m", envvar="GEMINI_MODEL", default=GEMINI_MODEL, show_default=True, help="Gemini model name.")
@click.option("--aspect-ratio", "-a", default="16:9", show_default=True, help="Aspect ratio hint passed to the model, e.g. 16:9 or 9:16.")
@click.option("--width", "-W", type=int, default=None, help="Target width in pixels. Triggers upscaling via Replicate if the generated image is smaller.")
@click.option("--height", "-H", type=int, default=None, help="Target height in pixels. Triggers upscaling via Replicate if the generated image is smaller.")
@click.option("--upscaler-model", "-u", envvar="REPLICATE_UPSCALER_MODEL", default=REPLICATE_UPSCALER_MODEL, show_default=True, help="Replicate upscaler model ID.")
@click.option("--upscaler-token", envvar="REPLICATE_API_TOKEN", default=None, help="Replicate API token for upscaling. Falls back to REPLICATE_API_TOKEN env var.")
@click.option("--reference-images", "-R", multiple=True, type=str, envvar="GEMINI_REFERENCE_IMAGES", help="Global reference images for style consistency (repeatable; env var: comma-separated paths).")
@click.option("--system-prompt-file", "-p", envvar="GEMINI_SYSTEM_PROMPT_FILE", type=click.Path(exists=True), help="Path to a text file that replaces the built-in system prompt.")
@click.option("--debug", is_flag=True, default=False, help="Print raw API request and response (binary blobs truncated).")
def main(api_key, input_yaml, output_dir, global_temp, model, aspect_ratio,
         width, height, upscaler_model, upscaler_token, reference_images, system_prompt_file, debug):
    """Generate images using the Gemini API from a YAML prompt file."""
    if len(reference_images) == 1 and "," in reference_images[0]:
        reference_images = [p.strip() for p in reference_images[0].split(",")]

    if system_prompt_file:
        with open(system_prompt_file, "r", encoding="utf-8") as f:
            system_instruction = f.read().strip()
    else:
        system_instruction = SYSTEM_RULES.strip()

    client = genai.Client(api_key=api_key)

    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    yaml_dir = os.path.dirname(os.path.abspath(input_yaml))
    total_cost = 0.0

    for i, item in enumerate(data.get("images", [])):
        current_ratio = item.get("aspect_ratio", aspect_ratio)
        current_width = item.get("width", width)
        current_height = item.get("height", height)
        current_upscaler = item.get("upscaler_model", upscaler_model)
        filename = item.get("filename") or f"image_{i:03d}.png"
        final_output_path = os.path.join(output_dir, filename)

        local_refs = [os.path.join(yaml_dir, r) for r in item.get("reference_images", [])]
        all_refs = list(reference_images) + local_refs

        click.echo(
            f"({i+1}) refs={len(all_refs)} -> {os.path.basename(final_output_path)}",
            nl=False,
        )

        cost = run_generation(
            client, model, system_instruction, item.get("prompt"),
            final_output_path, all_refs, current_ratio,
            item.get("temperature", global_temp),
            item.get("allow_text", False),
            debug=debug,
        )

        if cost > 0:
            click.secho(f" [~{cost:.4f}$]", fg="cyan", nl=False)
            total_cost += cost

            if upscaler_token and current_upscaler and (current_width or current_height):
                upscale_cost = run_upscale(
                    upscaler_token, current_upscaler, final_output_path,
                    current_width, current_height,
                )
                total_cost += upscale_cost
                if upscale_cost > 0:
                    click.secho(f" [+~{upscale_cost:.3f}$]", fg="cyan", nl=False)

        click.echo("")

    click.echo("-" * 40)
    click.secho(f"Estimated total cost: {total_cost:.4f}$", fg="green", bold=True)
    click.echo("-" * 40)
