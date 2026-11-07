"""Interface every camera backend implements."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


class CameraError(Exception):
    """A camera problem the user can act on; shown without a traceback."""


@dataclass(frozen=True, order=True)
class Mode:
    width: int
    height: int
    fps: float

    def __str__(self) -> str:
        return f"{self.width}x{self.height}@{self.fps:g}"


@dataclass
class Device:
    """A connected camera, as found by Camera.discover()."""

    backend: str
    name: str
    detail: str  # tells apart two cameras of the same model
    config: dict  # the config keys that select this device
    modes: list[Mode] = field(default_factory=list)  # empty if it cannot be recorded

    def __str__(self) -> str:
        selector = ", ".join(str(value) for value in self.config.values())
        modes = " ".join(str(mode) for mode in self.modes) or "no usable modes"
        return f"{self.name} ({self.detail}): {selector}\n    {modes}"


class Camera(ABC):
    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def discover(cls) -> list[Device]:
        """Return the connected devices of this type."""
        return []

    @classmethod
    @abstractmethod
    def matches(cls, config: dict, device: Device) -> bool:
        """Return whether a config file is for this device."""

    @classmethod
    @abstractmethod
    def mode_config(cls, mode: Mode) -> dict:
        """Return the config keys that select this mode."""

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
