import os
import base64

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(usecwd=True))

import click
import yaml
import requests

from ai_draw.common import SYSTEM_RULES, clean_multiline_string, safe_makedirs

OR_MODEL = "black-forest-labs/flux.2-pro"
OR_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _get_image_bytes(message: dict) -> bytes | None:
    """Extract image bytes from an OpenRouter response message.

    Handles two formats:
    - message['images'][0]['image_url']['url'] — base64 data URL (FLUX)
    - message['content'] as str/list with image_url parts — regular URL
    """
    # FLUX format: images list in message
    images = message.get("images")
    if images:
        url = images[0].get("image_url", {}).get("url", "")
        if url.startswith("data:"):
            _, data = url.split(",", 1)
            return base64.b64decode(data)
        if url:
            return requests.get(url, timeout=60).content

    # Fallback: content field
    content = message.get("content") or ""
    if isinstance(content, str) and content.strip():
        url = content.strip()
        if url.startswith("data:"):
            _, data = url.split(",", 1)
            return base64.b64decode(data)
        return requests.get(url, timeout=60).content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    _, data = url.split(",", 1)
                    return base64.b64decode(data)
                if url:
                    return requests.get(url, timeout=60).content
    return None


def generate_via_openrouter(api_key, model_id, prompt, system_rules, output_path, width=1920, height=1080, temp=0.3):
    if os.path.exists(output_path):
        click.secho(f"   Skipping: {os.path.basename(output_path)}", fg="yellow")
        return False

    full_prompt = f"{clean_multiline_string(system_rules)}\n\n{clean_multiline_string(prompt)}"

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": full_prompt}],
        "width": width,
        "height": height,
    }

    try:
        response = requests.post(
            OR_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        if not response.ok:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            click.secho(f"   Error {response.status_code}: {detail}", fg="red")
            return False
        choices = response.json().get("choices", [])
        if choices:
            img_bytes = _get_image_bytes(choices[0].get("message", {}))
            if img_bytes:
                safe_makedirs(output_path)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                return True
        click.secho("   Error: no image in response", fg="red")
    except Exception as e:
        click.secho(f"   Error: {e}", fg="red")
    return False


@click.command()
@click.option("--api-key", envvar="OPENROUTER_API_KEY", required=True, help="OpenRouter API key.")
@click.option("--input-yaml", "-f", type=click.Path(exists=True), required=True, help="Path to prompts YAML file.")
@click.option("--output-dir", "-d", default="output", show_default=True, help="Output directory for generated images.")
@click.option("--global-temp", "-t", type=float, default=0.3, show_default=True, help="Default generation temperature.")
@click.option("--model", "-m", envvar="OR_MODEL", default=OR_MODEL, show_default=True, help="OpenRouter model ID.")
@click.option("--width", "-W", default=1920, show_default=True, help="Output image width in pixels.")
@click.option("--height", "-H", default=1080, show_default=True, help="Output image height in pixels.")
@click.option("--system-prompt-file", "-p", envvar="OR_SYSTEM_PROMPT_FILE", type=click.Path(exists=True), help="Path to a text file that replaces the built-in system prompt.")
def main(api_key, input_yaml, output_dir, global_temp, model, width, height, system_prompt_file):
    """Generate images using OpenRouter image models from a YAML prompt file."""
    if system_prompt_file:
        with open(system_prompt_file, "r", encoding="utf-8") as f:
            system_rules = f.read()
    else:
        system_rules = SYSTEM_RULES

    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    for i, item in enumerate(data.get("images", [])):
        current_model = item.get("model", model)
        current_w = item.get("width", width)
        current_h = item.get("height", height)
        filename = item.get("filename") or f"image_{i:03d}.png"
        final_path = os.path.join(output_dir, filename)

        click.echo(f"({i+1}) [{current_model}] {current_w}x{current_h} -> {filename}")
        generate_via_openrouter(
            api_key, current_model, item.get("prompt"), system_rules,
            final_path, current_w, current_h, item.get("temperature", global_temp),
        )
