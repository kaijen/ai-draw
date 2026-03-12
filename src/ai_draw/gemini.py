import os

import click
import yaml
import PIL.Image
import google.generativeai as genai

from ai_draw.common import SYSTEM_RULES, clean_multiline_string, safe_makedirs

# Pricing constants (USD per 1M tokens / per image)
PRICE_PER_1M_INPUT = 0.075
PRICE_PER_1M_OUTPUT = 0.30
PRICE_PER_IMAGE = 0.003

GEMINI_MODEL = "gemini-2.0-flash-preview-image-generation"


def calculate_costs(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1_000_000) * PRICE_PER_1M_INPUT
    output_cost = (output_tokens / 1_000_000) * PRICE_PER_1M_OUTPUT
    return input_cost + output_cost + PRICE_PER_IMAGE


def run_generation(model, prompt, reference_path, output_path, aspect_ratio="16:9", temp=0.3):
    if os.path.exists(output_path):
        click.secho(f"   Skipping: {os.path.basename(output_path)}", fg="yellow")
        return 0, 0, 0

    content = []
    if reference_path and os.path.exists(reference_path):
        ref_img = PIL.Image.open(reference_path)
        content.append(ref_img)
        content.append("Use this image as a visual reference.")

    content.append(f"Subject in {aspect_ratio} format: {clean_multiline_string(prompt)}")
    config = genai.types.GenerationConfig(temperature=temp, aspect_ratio=aspect_ratio)

    try:
        response = model.generate_content(content, generation_config=config)

        usage = response.usage_metadata
        in_t = usage.prompt_token_count
        out_t = usage.candidates_token_count
        cost = calculate_costs(in_t, out_t)

        if response.candidates:
            safe_makedirs(output_path)
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data"):
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)
                    return in_t, out_t, cost
    except Exception as e:
        click.secho(f"   Error: {e}", fg="red")
    return 0, 0, 0


@click.command()
@click.option("--api-key", envvar="GEMINI_API_KEY", required=True, help="Gemini API key.")
@click.option("--input-yaml", "-f", type=click.Path(exists=True), required=True, help="Path to prompts YAML file.")
@click.option("--global-ref", "-r", type=click.Path(exists=True), help="Global reference image for style consistency.")
@click.option("--output-dir", "-d", default="output", show_default=True, help="Output directory for generated images.")
@click.option("--global-temp", "-t", type=float, default=0.3, show_default=True, help="Default generation temperature.")
def main(api_key, input_yaml, global_ref, output_dir, global_temp):
    """Generate images using the Gemini API from a YAML prompt file."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=clean_multiline_string(SYSTEM_RULES),
    )

    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    total_in, total_out, total_cost = 0, 0, 0.0

    for i, item in enumerate(data.get("images", [])):
        ratio = item.get("aspect_ratio", "16:9")
        current_temp = item.get("temperature", global_temp)
        filename = item.get("filename") or f"image_{i:03d}.png"
        final_output_path = os.path.join(output_dir, filename)

        click.echo(f"({i+1}) -> {os.path.basename(final_output_path)}", nl=False)

        in_t, out_t, cost = run_generation(
            model, item.get("prompt"), global_ref, final_output_path, ratio, current_temp
        )

        if in_t > 0:
            click.secho(f" [Tokens: {in_t} in / {out_t} out | ~{cost:.4f}$]", fg="cyan")
            total_in += in_t
            total_out += out_t
            total_cost += cost
        else:
            click.echo("")

    click.echo("-" * 40)
    click.secho("SUMMARY:", bold=True)
    click.echo(f"Tokens: {total_in} input / {total_out} output")
    click.secho(f"Estimated total cost: {total_cost:.4f}$", fg="green", bold=True)
    click.echo("-" * 40)
