"""USB webcams, through V4L2.

Packets are stored as the camera produced them, so recording costs no CPU and
no image quality. Only the preview decodes frames.
"""

import subprocess
import threading
from pathlib import Path

import av
import cv2
import numpy as np

from camera_recorder.cameras.base import Camera, CameraError

BY_ID = Path("/dev/v4l/by-id")
READ_TIMEOUT_S = 5.0


def _v4l2_ctl(*args: str) -> str:
    result = subprocess.run(["v4l2-ctl", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise CameraError(f"v4l2-ctl {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


class _Writer:
    """Writes one recording: video.mkv plus a timestamp for every frame."""

    def __init__(self, out_dir: Path, stream: av.VideoStream, fps: float):
        self._nominal_gap = 1 / fps
        self._output = av.open(str(out_dir / "video.mkv"), "w")
        self._stream = self._output.add_stream_from_template(stream)
        self._csv = open(out_dir / "timestamps.csv", "w")
        self._csv.write("frame,timestamp_unix_s,video_time_s\n")
        self._first_pts = None
        self._frames = 0
        self._first_time = self._last_time = None
        self._max_gap = 0.0
        self._dropped = 0

    def write(self, packet: av.Packet) -> None:
        timestamp = float(packet.pts * packet.time_base)
        if self._first_pts is None:
            self._first_pts = packet.pts
            self._first_time = timestamp
        else:
            gap = timestamp - self._last_time
            self._max_gap = max(self._max_gap, gap)
            if gap > 1.5 * self._nominal_gap:
                self._dropped += round(gap / self._nominal_gap) - 1
        self._last_time = timestamp

        # The capture clock is Unix time. The video starts at 0 so that players
        # work; timestamps.csv keeps the absolute time for syncing with other data.
        packet.pts -= self._first_pts
        packet.dts = packet.pts
        self._csv.write(
            f"{self._frames},{timestamp:.6f},{float(packet.pts * packet.time_base):.6f}\n"
        )
        packet.stream = self._stream
        self._output.mux(packet)
        self._frames += 1

    def close(self) -> dict:
        self._output.close()
        self._csv.close()
        duration = (self._last_time - self._first_time) if self._frames > 1 else 0.0
        return {
            "frames": self._frames,
            "first_frame_unix_s": self._first_time,
            "last_frame_unix_s": self._last_time,
            "duration_s": round(duration, 3),
            "mean_fps": round((self._frames - 1) / duration, 3) if duration else None,
            "max_frame_gap_ms": round(self._max_gap * 1000, 1),
            "estimated_dropped_frames": self._dropped,
        }


class WebcamCamera(Camera):
    def __init__(self, config: dict):
        super().__init__(config)
        self._device = config["device"]
        self._input = None
        self._stream = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._writer = None
        self._latest = None
        self._error = None

    @classmethod
    def discover(cls) -> list[str]:
        if not BY_ID.is_dir():
            return []
        return [
            f"{link} -> {link.resolve()}"
            for link in sorted(BY_ID.glob("*-video-index0"))
            if "realsense" not in link.name.lower()
        ]

    def open(self) -> None:
        if not Path(self._device).exists():
            raise CameraError(f"device not found: {self._device} (see `camrec list`)")

        # Order matters: a manual value is rejected while its auto mode is on.
        for name, value in self.config.get("controls", {}).items():
            _v4l2_ctl("-d", self._device, f"--set-ctrl={name}={value}")

        width, height, fps = self.config["width"], self.config["height"], self.config["fps"]
        try:
            self._input = av.open(
                self._device,
                format="v4l2",
                options={
                    "input_format": "mjpeg",
                    "video_size": f"{width}x{height}",
                    "framerate": str(fps),
                    "ts": "mono2abs",  # kernel capture time, as Unix time
                },
                timeout=READ_TIMEOUT_S,
            )
        except av.FFmpegError as e:
            raise CameraError(f"cannot open {self._device}: {e}") from e

        self._stream = self._input.streams.video[0]
        actual = (self._stream.width, self._stream.height)
        if actual != (width, height):
            self._input.close()
            raise CameraError(f"camera gave {actual[0]}x{actual[1]}, asked for {width}x{height}")

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        # Runs apart from the preview so a slow window never costs recorded frames.
        try:
            for packet in self._input.demux(self._stream):
                if self._stop.is_set():
                    return
                # Some webcams send an empty packet as the first one of a stream.
                if packet.pts is None or packet.size == 0:
                    continue
                data = bytes(packet)
                with self._lock:
                    self._latest = data
                    if self._writer is not None:
                        self._writer.write(packet)
        except Exception as e:
            self._error = e

    def check(self) -> None:
        if self._error is not None:
            raise CameraError(f"capture failed on {self._device}: {self._error}")

    def preview(self) -> np.ndarray | None:
        with self._lock:
            data, self._latest = self._latest, None
        if data is None:
            return None
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    def start_recording(self, out_dir: Path) -> None:
        writer = _Writer(out_dir, self._stream, self.config["fps"])
        with self._lock:
            self._writer = writer

    def stop_recording(self) -> dict:
        with self._lock:
            writer, self._writer = self._writer, None
        return writer.close()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=READ_TIMEOUT_S)
        if self._input is not None:
            self._input.close()

    def describe(self) -> dict:
        return {
            "device": self._device,
            "resolved_device": str(Path(self._device).resolve()),
            "codec": "mjpeg",
            "controls": [
                line.strip()
                for line in _v4l2_ctl("-d", self._device, "--list-ctrls").splitlines()
                if ":" in line
            ],
        }
