from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ai-draw")
except PackageNotFoundError:
    __version__ = "unknown"
