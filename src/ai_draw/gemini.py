import os

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import click
import yaml
from google import genai
from google.genai import types

from ai_draw.common import SYSTEM_RULES, clean_multiline_string, safe_makedirs

PRICE_PER_IMAGE = 0.003

GEMINI_MODEL = "gemini-2.5-flash-preview-04-17"


def run_generation(client, model_name, system_instruction, prompt, output_path, aspect_ratio="16:9", temp=0.3):
    if os.path.exists(output_path):
        click.secho(f"   Skipping: {os.path.basename(output_path)}", fg="yellow")
        return 0.0

    safe_makedirs(output_path)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=clean_multiline_string(prompt),
            config=types.GenerateContentConfig(
                system_instruction=clean_multiline_string(system_instruction),
                temperature=temp,
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
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
@click.option("--system-prompt-file", "-p", envvar="GEMINI_SYSTEM_PROMPT_FILE", type=click.Path(exists=True), help="Path to a text file that replaces the built-in system prompt.")
def main(api_key, input_yaml, output_dir, global_temp, model, aspect_ratio, system_prompt_file):
    """Generate images using the Gemini API from a YAML prompt file."""
    if system_prompt_file:
        with open(system_prompt_file, "r", encoding="utf-8") as f:
            system_instruction = clean_multiline_string(f.read())
    else:
        system_instruction = clean_multiline_string(SYSTEM_RULES)

    client = genai.Client(api_key=api_key)

    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    total_cost = 0.0

    for i, item in enumerate(data.get("images", [])):
        current_ratio = item.get("aspect_ratio", aspect_ratio)
        filename = item.get("filename") or f"image_{i:03d}.png"
        final_output_path = os.path.join(output_dir, filename)

        click.echo(f"({i+1}) -> {os.path.basename(final_output_path)}", nl=False)

        cost = run_generation(
            client, model, system_instruction, item.get("prompt"),
            final_output_path, current_ratio,
            item.get("temperature", global_temp),
        )

        if cost > 0:
            click.secho(f" [~{cost:.4f}$]", fg="cyan")
            total_cost += cost
        else:
            click.echo("")

    click.echo("-" * 40)
    click.secho(f"Estimated total cost: {total_cost:.4f}$", fg="green", bold=True)
    click.echo("-" * 40)
