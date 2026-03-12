import os
import base64

import click
import yaml
import requests

from ai_draw.common import SYSTEM_RULES, clean_multiline_string, safe_makedirs


def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_via_openrouter(api_key, model_id, prompt, output_path, ref_path=None, temp=0.3):
    if os.path.exists(output_path):
        click.secho(f"   Skipping: {os.path.basename(output_path)}", fg="yellow")
        return False

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    content = [{"type": "text", "text": f"{clean_multiline_string(SYSTEM_RULES)}\n\nSubject: {prompt}"}]

    if ref_path and os.path.exists(ref_path):
        b64 = encode_image_to_base64(ref_path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "temperature": temp,
        "modalities": ["image"],
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        res_data = response.json()

        if "choices" in res_data:
            img_data = res_data["choices"][0]["message"].get("images", [None])[0]
            if img_data:
                safe_makedirs(output_path)
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(img_data))
                return True
    except Exception as e:
        click.secho(f"   Error: {e}", fg="red")
    return False


@click.command()
@click.option("--api-key", envvar="OPENROUTER_API_KEY", required=True, help="OpenRouter API key.")
@click.option("--input-yaml", "-f", type=click.Path(exists=True), required=True, help="Path to prompts YAML file.")
@click.option("--global-ref", "-r", type=click.Path(exists=True), help="Global reference image for style consistency.")
@click.option("--output-dir", "-d", default="output", show_default=True, help="Output directory for generated images.")
@click.option("--global-temp", "-t", type=float, default=0.3, show_default=True, help="Default generation temperature.")
def main(api_key, input_yaml, global_ref, output_dir, global_temp):
    """Generate images using OpenRouter-compatible models from a YAML prompt file."""
    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    yaml_dir = os.path.dirname(os.path.abspath(input_yaml))

    for i, item in enumerate(data.get("images", [])):
        model_id = item.get("model", "google/gemini-2.0-flash-001")
        prompt = item.get("prompt")
        current_temp = item.get("temperature", global_temp)
        local_ref = item.get("reference_image")

        ref_path = os.path.join(yaml_dir, local_ref) if local_ref else global_ref

        filename = item.get("filename") or f"image_{i:03d}.png"
        final_path = os.path.join(output_dir, filename)

        click.echo(f"({i+1}) [{model_id}] -> {filename}")
        generate_via_openrouter(api_key, model_id, prompt, final_path, ref_path, current_temp)
