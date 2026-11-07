"""Register `camrec gui` with the desktop's app menu."""

import ctypes.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "camrec"  # also the Qt window class, which ties the window to its dock icon
ICON = Path(__file__).with_name("assets") / "camrec.svg"
ENTRY = """\
[Desktop Entry]
Type=Application
Name=Camera Recorder
Name[ko]=카메라 레코더
Comment=Scan cameras, preview and record experiments
Comment[ko]=카메라를 스캔하고 미리 보면서 실험을 녹화합니다
Keywords=camera;webcam;realsense;record;video;
Keywords[ko]=카메라;웹캠;리얼센스;녹화;영상;
Exec="{executable}" gui
Icon={icon}
Terminal=false
Categories=AudioVideo;Video;Recorder;
StartupWMClass={app_id}
"""


def _applications_dir() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share"
    return Path(data_home) / "applications"


def _refresh_menu() -> None:
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(_applications_dir())], check=False)


def qt_problem() -> str | None:
    """Return what would stop Qt from starting; Qt itself would abort the process."""
    on_x11 = "WAYLAND_DISPLAY" not in os.environ and "QT_QPA_PLATFORM" not in os.environ
    if on_x11 and ctypes.util.find_library("xcb-cursor") is None:
        return "Qt needs libxcb-cursor: run `sudo apt install libxcb-cursor0`"
    return None


def install() -> None:
    # sys.executable is this project's .venv, so the menu entry works without uv.
    executable = Path(sys.executable).with_name("camrec")
    path = _applications_dir() / f"{APP_ID}.desktop"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ENTRY.format(executable=executable, icon=ICON, app_id=APP_ID))
    _refresh_menu()
    print(f"registered -> {path}")
    print("search for 'Camera Recorder' (카메라 레코더) in the app menu")
    if problem := qt_problem():
        print(f"warning: the app will not start yet. {problem}")


def uninstall() -> None:
    path = _applications_dir() / f"{APP_ID}.desktop"
    path.unlink(missing_ok=True)
    _refresh_menu()
    print(f"removed -> {path}")
