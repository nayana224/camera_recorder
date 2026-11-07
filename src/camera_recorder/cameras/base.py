"""Interface every camera backend implements."""

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class CameraError(Exception):
    """A camera problem the user can act on; shown without a traceback."""


class Camera(ABC):
    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def discover(cls) -> list[str]:
        """Describe connected devices of this type, for `camrec list`."""
        return []

    @abstractmethod
    def open(self) -> None:
        """Start streaming. Recording starts separately."""

    @abstractmethod
    def close(self) -> None:
        """Stop streaming and release the device."""

    @abstractmethod
    def preview(self) -> np.ndarray | None:
        """Return the newest frame as BGR, or None if there is none yet."""

    @abstractmethod
    def start_recording(self, out_dir: Path) -> None:
        """Start writing files into out_dir."""

    @abstractmethod
    def stop_recording(self) -> dict:
        """Finish the files and return stats for metadata.json."""

    def check(self) -> None:
        """Raise CameraError if capture has failed since the last call."""

    def describe(self) -> dict:
        """Return device details for metadata.json."""
        return {}
