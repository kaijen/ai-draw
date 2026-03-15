import math
import os

import click
from PIL import Image
import replicate as replicate_lib

SYSTEM_RULES = """
Stil: Minimalistischer Strichmännchen-Stil (Stick Figure Art) mit runden Köpfen.
Optik: Handgezeichneter Whiteboard-Look; Flächen durch Schraffuren (Hatching),
keine Farbverläufe.
Farben: Reduzierte Palette in Schwarz-Weiß mit einem kräftigen Rot als
gezielte Akzentfarbe für wichtige Elemente.
Format: Erstelle alle Visualisierungen zwingend im angegebenen Seitenverhältnis und der angegebenen Auflösung in Pixeln.
Textverbot: In den Bildern darf absolut kein Text, keine Buchstaben und
keine Schriftzeichen verwendet werden.
Hintergrund: Schlichter, weißer Hintergrund ohne unnötige dekorative Symbole.
"""


def clean_multiline_string(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def safe_makedirs(output_path: str) -> None:
    """Create parent directories for output_path, handling bare filenames gracefully."""
    dir_part = os.path.dirname(output_path)
    if dir_part:
        os.makedirs(dir_part, exist_ok=True)


REPLICATE_UPSCALER_MODEL = "nightmareai/real-esrgan"

PRICE_PER_UPSCALE = 0.010


def run_upscale(replicate_token: str, upscaler_model: str, image_path: str,
                target_width: int | None, target_height: int | None) -> float:
    """Upscale image_path in-place if it is smaller than target dimensions.

    Scale factor is computed as ceil(max(target_w/actual_w, target_h/actual_h)).
    Returns cost, or 0.0 when no upscaling was needed or on error.
    """
    with Image.open(image_path) as img:
        actual_w, actual_h = img.size

    needs_upscale = (
        (target_width and actual_w < target_width) or
        (target_height and actual_h < target_height)
    )
    if not needs_upscale:
        return 0.0

    scale_x = math.ceil(target_width / actual_w) if target_width else 1
    scale_y = math.ceil(target_height / actual_h) if target_height else 1
    scale_factor = max(scale_x, scale_y)

    click.echo(
        f"\n   Upscaling {actual_w}x{actual_h} -> ~{actual_w*scale_factor}x{actual_h*scale_factor}"
        f" (scale={scale_factor}, model={upscaler_model})",
        nl=False,
    )

    try:
        client = replicate_lib.Client(api_token=replicate_token)
        output = client.run(
            upscaler_model,
            input={"image": open(image_path, "rb"), "scale": scale_factor},
        )
        file_output = output[0] if isinstance(output, list) else output
        data = file_output.read() if hasattr(file_output, "read") else file_output
        with open(image_path, "wb") as f:
            f.write(data)
        return PRICE_PER_UPSCALE
    except Exception as e:
        click.secho(f"\n   Error upscaling: {e}", fg="red")
        return 0.0
