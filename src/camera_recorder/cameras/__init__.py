"""Camera backends. To add one, see "새 카메라 추가" in README.md."""

import importlib

from camera_recorder.cameras.base import Camera, CameraError, Device, Mode

# Imported on demand so a missing SDK only affects its own backend.
BACKENDS = {
    "webcam": "camera_recorder.cameras.webcam:WebcamCamera",
    "realsense": "camera_recorder.cameras.realsense:RealSenseCamera",
}


def load_backend(name: str) -> type[Camera]:
    if name not in BACKENDS:
        raise CameraError(f"unknown backend {name!r} (available: {', '.join(BACKENDS)})")
    module, cls = BACKENDS[name].split(":")
    return getattr(importlib.import_module(module), cls)
