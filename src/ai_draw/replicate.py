import os
import urllib.request

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import click
import yaml
import replicate as replicate_lib

from ai_draw.common import (
    SYSTEM_RULES, REPLICATE_UPSCALER_MODEL, PRICE_PER_UPSCALE,
    clean_multiline_string, safe_makedirs, run_upscale,
)

REPLICATE_MODEL = "black-forest-labs/flux-2-pro"

PRICE_PER_IMAGE = 0.055


def _read_file_output(file_output) -> bytes:
    """Read bytes from a replicate FileOutput or a plain URL string."""
    if isinstance(file_output, str):
        with urllib.request.urlopen(file_output) as resp:
            return resp.read()
    return file_output.read()


def run_generation(client, model_id, system_prompt, prompt, output_path,
                   aspect_ratio: str = "16:9",
                   width: int | None = None, height: int | None = None,
                   reference_images: list[str] | None = None,
                   guidance_scale: float | None = None,
                   negative_prompt: str | None = None) -> float:
    """Generate one image. Returns cost, or 0.0 on skip/error."""
    if os.path.exists(output_path):
        click.secho(f"   Skipping: {os.path.basename(output_path)}", fg="yellow")
        return 0.0

    safe_makedirs(output_path)

    full_prompt = (
        f"{system_prompt}\n\n{clean_multiline_string(prompt)}"
        if system_prompt
        else clean_multiline_string(prompt)
    )

    api_input = {
        "prompt": full_prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": "png",
    }
    if aspect_ratio == "custom":
        if width:
            api_input["width"] = width
        if height:
            api_input["height"] = height
    if reference_images:
        # input_images: Flux-compatible; reference_images: SeedDream-compatible
        image_handles = [open(p, "rb") for p in reference_images]
        api_input["input_images"] = image_handles
        api_input["reference_images"] = image_handles
    if guidance_scale is not None:
        api_input["guidance_scale"] = guidance_scale
    if negative_prompt:
        api_input["negative_prompt"] = negative_prompt

    try:
        output = client.run(
            model_id,
            input=api_input,
        )
        file_output = output[0] if isinstance(output, list) else output
        with open(output_path, "wb") as f:
            f.write(_read_file_output(file_output))
        return PRICE_PER_IMAGE
    except Exception as e:
        click.secho(f"   Error generating: {e}", fg="red")
        return 0.0



@click.command()
@click.option("--api-key", envvar="REPLICATE_API_TOKEN", required=True, help="Replicate API token.")
@click.option("--input-yaml", "-f", type=click.Path(exists=True), required=True, help="Path to prompts YAML file.")
@click.option("--output-dir", "-d", default="output", show_default=True, help="Output directory for generated images.")
@click.option("--model", "-m", envvar="REPLICATE_MODEL", default=REPLICATE_MODEL, show_default=True, help="Replicate model ID.")
@click.option("--aspect-ratio", "-a", default="16:9", show_default=True, help="Output aspect ratio, e.g. 16:9 or 9:16.")
@click.option("--width", "-W", type=int, default=None, help="Target width in pixels. Triggers upscaling if the generated image is smaller.")
@click.option("--height", "-H", type=int, default=None, help="Target height in pixels. Triggers upscaling if the generated image is smaller.")
@click.option("--upscaler-model", "-u", envvar="REPLICATE_UPSCALER_MODEL", default=REPLICATE_UPSCALER_MODEL, show_default=True, help="Replicate upscaler model ID. Used when --width/--height are set.")
@click.option("--reference-images", "-R", multiple=True, type=str, envvar="REPLICATE_REFERENCE_IMAGES", help="Global reference images for style consistency (repeatable; env var: comma-separated paths).")
@click.option("--guidance-scale", "-g", type=float, default=None, envvar="REPLICATE_GUIDANCE_SCALE", help="Guidance scale (prompt adherence). Supported by SeedDream and similar models.")
@click.option("--negative-prompt", "-n", type=str, default=None, envvar="REPLICATE_NEGATIVE_PROMPT", help="Negative prompt (what to exclude). Supported by SeedDream and similar models.")
@click.option("--system-prompt-file", "-p", envvar="REPLICATE_SYSTEM_PROMPT_FILE", type=click.Path(exists=True), help="Path to a text file that replaces the built-in system prompt.")
def main(api_key, input_yaml, output_dir, model, aspect_ratio, width, height,
         upscaler_model, reference_images, guidance_scale, negative_prompt, system_prompt_file):
    """Generate images using the Replicate API from a YAML prompt file."""
    # Env var delivers a single comma-separated string; split it into individual paths.
    if len(reference_images) == 1 and "," in reference_images[0]:
        reference_images = [p.strip() for p in reference_images[0].split(",")]

    if system_prompt_file:
        with open(system_prompt_file, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
    else:
        system_prompt = SYSTEM_RULES.strip()

    client = replicate_lib.Client(api_token=api_key)

    yaml_dir = os.path.dirname(os.path.abspath(input_yaml))

    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    total_cost = 0.0

    for i, item in enumerate(data.get("images", [])):
        current_model = item.get("model", model)
        current_ratio = item.get("aspect_ratio", aspect_ratio)
        current_width = item.get("width", width)
        current_height = item.get("height", height)
        current_upscaler = item.get("upscaler_model", upscaler_model)
        current_guidance = item.get("guidance_scale", guidance_scale)
        current_negative = item.get("negative_prompt", negative_prompt)
        filename = item.get("filename") or f"image_{i:03d}.png"
        final_output_path = os.path.join(output_dir, filename)

        local_refs = [os.path.join(yaml_dir, r) for r in item.get("reference_images", [])]
        all_refs = list(reference_images) + local_refs or None

        click.echo(
            f"({i+1}) {current_model} -> {os.path.basename(final_output_path)}",
            nl=False,
        )

        gen_cost = run_generation(
            client, current_model, system_prompt,
            item.get("prompt"), final_output_path, current_ratio,
            current_width, current_height, all_refs,
            current_guidance, current_negative,
        )
        total_cost += gen_cost

        if gen_cost > 0:
            click.secho(f" [~{gen_cost:.3f}$]", fg="cyan", nl=False)

            if current_upscaler and (current_width or current_height):
                upscale_cost = run_upscale(
                    api_key, current_upscaler, final_output_path,
                    current_width, current_height,
                )
                total_cost += upscale_cost
                if upscale_cost > 0:
                    click.secho(f" [+~{upscale_cost:.3f}$]", fg="cyan", nl=False)

        click.echo("")

    click.echo("-" * 40)
    click.secho(f"Estimated total cost: {total_cost:.3f}$", fg="green", bold=True)
    click.echo("-" * 40)
