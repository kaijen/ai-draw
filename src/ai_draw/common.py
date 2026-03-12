import os

SYSTEM_RULES = """
Stil: Minimalistischer Strichmännchen-Stil (Stick Figure Art) mit runden Köpfen.
Optik: Handgezeichneter Whiteboard-Look; Flächen durch Schraffuren (Hatching),
keine Farbverläufe.
Farben: Reduzierte Palette in Schwarz-Weiß mit einem kräftigen Rot als
gezielte Akzentfarbe für wichtige Elemente.
Format: Erstelle alle Visualisierungen zwingend im Seitenverhältnis 16:9 mit einer Auflösung von 1920x1080 Pixeln.
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
