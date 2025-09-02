"""VSensor communication library."""

from importlib import metadata as _metadata

try:
    __version__ = _metadata.version("vsensor")
except _metadata.PackageNotFoundError:  # pragma: no cover - package not installed
    __version__ = "0.0.0"

from .client import VSensorClient
from .config import Config
from .models import Telemetry, Mode
__all__ = ["VSensorClient", "Config", "Telemetry", "Mode", "__version__"]
