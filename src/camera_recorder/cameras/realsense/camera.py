"""Intel RealSense, through the librealsense SDK.

Recording uses the SDK's .bag writer, which is switched on by restarting the
pipeline, so the stream pauses briefly at each start and stop.
"""

from pathlib import Path

import numpy as np

from camera_recorder.cameras.base import Camera, CameraError, Device, Mode

try:
    import pyrealsense2 as rs
except ImportError as e:
    raise CameraError("pyrealsense2 is missing: run `uv sync --extra realsense`") from e


def _stream_modes(device, stream, stream_format) -> set[Mode]:
    modes = set()
    for sensor in device.query_sensors():
        for profile in sensor.get_stream_profiles():
            if profile.stream_type() == stream and profile.format() == stream_format:
                video = profile.as_video_stream_profile()
                modes.add(Mode(video.width(), video.height(), profile.fps()))
    return modes


class RealSenseCamera(Camera):
    def __init__(self, config: dict):
        super().__init__(config)
        self._pipeline = rs.pipeline()
        self._info = {}

    @classmethod
    def discover(cls) -> list[Device]:
        devices = []
        for device in rs.context().query_devices():
            serial = device.get_info(rs.camera_info.serial_number)
            # One mode drives both streams, so offer what color and depth share.
            modes = _stream_modes(device, rs.stream.color, rs.format.bgr8)
            modes &= _stream_modes(device, rs.stream.depth, rs.format.z16)
            name = device.get_info(rs.camera_info.name)
            devices.append(Device("realsense", name, serial, {"serial": serial}, sorted(modes)))
        return devices

    @classmethod
    def matches(cls, config: dict, device: Device) -> bool:
        serial = config.get("serial")
        return serial is None or str(serial) == device.config["serial"]

    @classmethod
    def mode_config(cls, mode: Mode) -> dict:
        stream = {"width": mode.width, "height": mode.height, "fps": mode.fps}
        return {"color": stream, "depth": stream}

    def _start(self, bag: Path | None = None) -> None:
        rs_config = rs.config()
        if self.config.get("serial"):
            rs_config.enable_device(str(self.config["serial"]))
        color, depth = self.config["color"], self.config["depth"]
        rs_config.enable_stream(
            rs.stream.color, color["width"], color["height"], rs.format.bgr8, color["fps"]
        )
        rs_config.enable_stream(
            rs.stream.depth, depth["width"], depth["height"], rs.format.z16, depth["fps"]
        )
        if bag is not None:
            rs_config.enable_record_to_file(str(bag))
        try:
            # The returned profile is not kept: a live reference holds the .bag open.
            device = self._pipeline.start(rs_config).get_device()
            self._info = {
                "name": device.get_info(rs.camera_info.name),
                "serial": device.get_info(rs.camera_info.serial_number),
                "firmware": device.get_info(rs.camera_info.firmware_version),
            }
        except RuntimeError as e:
            raise CameraError(f"cannot start RealSense: {e}") from e

    def open(self) -> None:
        self._start()

    def close(self) -> None:
        self._pipeline.stop()

    def preview(self) -> np.ndarray | None:
        frames = self._pipeline.poll_for_frames()
        if not frames:
            return None
        color = frames.get_color_frame()
        return np.asanyarray(color.get_data()).copy() if color else None

    def start_recording(self, out_dir: Path) -> None:
        self._pipeline.stop()
        self._start(out_dir / "recording.bag")

    def stop_recording(self) -> dict:
        self._pipeline.stop()
        self._start()
        return {"file": "recording.bag"}

    def describe(self) -> dict:
        return self._info
