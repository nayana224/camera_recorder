"""The record loop and session folders, shared by every camera backend."""

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2

from camera_recorder.cameras import Camera, CameraError

WINDOW = "camrec"
KEY_ESC = 27


@dataclass
class Session:
    path: Path
    started_at: str
    monotonic_start: float


def start_session(camera: Camera, root: Path, name: str, label: str | None) -> Session:
    now = datetime.now().astimezone()
    folder = now.strftime("%Y%m%d_%H%M%S")
    if label:
        folder += "_" + re.sub(r"[^\w-]+", "-", label)
    path = root / name / folder
    suffix = 1
    while path.exists():
        suffix += 1
        path = root / name / f"{folder}_{suffix}"
    path.mkdir(parents=True)

    camera.start_recording(path)
    print(f"recording -> {path}", flush=True)
    return Session(path, now.isoformat(timespec="milliseconds"), time.monotonic())


def stop_session(camera: Camera, session: Session, name: str, label: str | None) -> dict:
    stats = camera.stop_recording()
    try:
        device = camera.describe()
    except CameraError as e:  # an unplugged camera must not cost the metadata
        device = {"error": str(e)}
    metadata = {
        "camera": name,
        "label": label,
        "started_at": session.started_at,
        "stopped_at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "config": camera.config,
        "device": device,
        "stats": stats,
    }
    (session.path / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    print(f"saved -> {session.path}\n  {json.dumps(stats)}", flush=True)
    return stats


def run(
    camera: Camera,
    name: str,
    root: Path,
    label: str | None = None,
    duration: float | None = None,
    show_preview: bool = True,
) -> None:
    """Stream until quit. Records on Space, or at once with duration or no preview."""
    session = None
    window_open = False
    camera.open()
    try:
        if duration is not None or not show_preview:
            session = start_session(camera, root, name, label)
        if show_preview:
            print("Space: start/stop recording, q or Esc: quit", flush=True)
        elif duration is None:
            print("Ctrl+C: stop", flush=True)

        while True:
            camera.check()
            if session and duration and time.monotonic() - session.monotonic_start >= duration:
                break
            if not show_preview:
                time.sleep(0.02)
                continue

            frame = camera.preview()
            if frame is not None:
                if session:
                    elapsed = time.monotonic() - session.monotonic_start
                    cv2.putText(
                        frame, f"REC {elapsed:.1f}s", (24, 56), cv2.FONT_HERSHEY_SIMPLEX,
                        1.4, (0, 0, 255), 3,
                    )
                if not window_open:
                    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
                    window_open = True
                cv2.imshow(WINDOW, frame)

            key = cv2.waitKey(10) & 0xFF
            if key in (ord("q"), KEY_ESC):
                break
            if window_open and cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == ord(" "):
                if session:
                    stop_session(camera, session, name, label)
                    session = None
                else:
                    session = start_session(camera, root, name, label)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if session:
                stop_session(camera, session, name, label)
        finally:
            camera.close()
            if window_open:
                cv2.destroyAllWindows()
