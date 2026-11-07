"""Desktop UI, `camrec gui`: scan cameras, pick a mode, preview and record."""

import queue
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import yaml
from PySide6.QtCore import QRect, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from camera_recorder.cameras import BACKENDS, CameraError, Device, Mode, load_backend
from camera_recorder.cli import CONFIG_DIR
from camera_recorder.desktop import APP_ID, ICON, qt_problem
from camera_recorder.session import Session, start_session, stop_session

PANEL_WIDTH = 320
IDLE_WAIT_MS = 5
REC_TICK_MS = 100
SIGNAL_POLL_MS = 200
STATS_SHOWN = ("frames", "duration_s", "mean_fps", "estimated_dropped_frames")
RECORD_STYLE = "font-weight: bold; padding: 10px;"
STOP_STYLE = RECORD_STYLE + "background-color: #c62828; color: white;"


def scan() -> tuple[list[Device], list[str]]:
    """Return the connected cameras, and why any backend could not be asked."""
    devices, problems = [], []
    for backend in BACKENDS:
        try:
            devices += load_backend(backend).discover()
        except Exception as e:  # one backend's SDK must not hide the other cameras
            problems.append(f"{backend}: {e}")
    return devices, problems


def config_for(device: Device) -> tuple[str, dict]:
    """Return the device's configs/*.yaml, or a blank config named after the device.

    Using the file keeps its `controls` and recordings folder the same as
    `camrec record`.
    """
    backend = load_backend(device.backend)
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        config = yaml.safe_load(path.read_text())
        if config["backend"] == device.backend and backend.matches(config, device):
            return path.stem, config
    return re.sub(r"[^\w-]+", "_", device.name).strip("_"), {"backend": device.backend}


class CameraWorker(QThread):
    """Owns the open camera. Every camera call happens on this thread.

    The RealSense backend restarts its pipeline to start and stop recording, which
    takes seconds and must not overlap a preview call.
    """

    opened = Signal()
    frame = Signal(QImage)
    recording_started = Signal(object)  # Session
    recording_stopped = Signal(object, object)  # Session, stats
    recording_refused = Signal(str)
    failed = Signal(str)

    def __init__(self, config: dict, name: str, parent: QWidget):
        super().__init__(parent)
        self._config = config
        self._name = name
        self._commands = queue.Queue()
        self._session = None
        self._label = None

    def begin_recording(self, root: Path, label: str | None) -> None:
        self._commands.put(("begin", root, label))

    def end_recording(self) -> None:
        self._commands.put(("end",))

    def shutdown(self) -> None:
        self._commands.put(("shutdown",))

    def run(self) -> None:
        try:
            camera = load_backend(self._config["backend"])(self._config)
            camera.open()
        except Exception as e:
            self.failed.emit(str(e))
            return

        error = None
        try:
            self.opened.emit()
            self._stream(camera)
        except Exception as e:
            error = e
        try:
            self._end_session(camera)  # keeps a recording whose camera just failed
        except Exception as e:
            error = error or e
        try:
            camera.close()
        except Exception as e:
            error = error or e
        if error is not None:
            self.failed.emit(str(error))

    def _stream(self, camera) -> None:
        while True:
            try:
                command, *args = self._commands.get_nowait()
            except queue.Empty:
                command = None
            if command == "shutdown":
                return
            if command == "begin":
                self._begin_session(camera, *args)
            elif command == "end":
                self._end_session(camera)

            camera.check()
            frame = camera.preview()
            if frame is None:
                self.msleep(IDLE_WAIT_MS)
            else:
                self.frame.emit(_to_qimage(frame))

    def _begin_session(self, camera, root: Path, label: str | None) -> None:
        try:
            self._session = start_session(camera, root, self._name, label)
        except (CameraError, OSError) as e:
            self.recording_refused.emit(str(e))
            return
        self._label = label
        self.recording_started.emit(self._session)

    def _end_session(self, camera) -> None:
        session, self._session = self._session, None
        if session is not None:
            stats = stop_session(camera, session, self._name, self._label)
            self.recording_stopped.emit(session, stats)


def _to_qimage(frame: np.ndarray) -> QImage:
    height, width = frame.shape[:2]
    # copy(): QImage only borrows the array's memory, and this outlives the array.
    return QImage(frame.data, width, height, frame.strides[0], QImage.Format.Format_BGR888).copy()


class Preview(QWidget):
    """Shows the newest frame. Text drawn here never reaches the recording."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(480, 270)
        self._image = None
        self._message = ""
        self._overlay = ""

    def show_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def show_message(self, message: str) -> None:
        self._image = None
        self._message = message
        self.update()

    def set_overlay(self, text: str) -> None:
        self._overlay = text
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._image is None:
            painter.setPen(Qt.GlobalColor.lightGray)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._message)
        else:
            target = QRect()
            target.setSize(self._image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio))
            target.moveCenter(self.rect().center())
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(target, self._image)
        if self._overlay:
            font = QFont(self.font())
            font.setPointSize(18)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#ff3b30"))
            painter.drawText(self.rect().adjusted(16, 12, -16, -12), Qt.AlignmentFlag.AlignTop, self._overlay)


class MainWindow(QMainWindow):
    def __init__(self, root: Path):
        super().__init__()
        self.setWindowTitle("Camera Recorder")
        self._default_root = root
        self._devices = []
        self._device = None
        self._name = ""
        self._config = {}
        self._worker = None
        self._streaming = False
        self._session = None
        self._transition = False  # waiting for the worker to start or stop recording

        self._rec_timer = QTimer(self)
        self._rec_timer.setInterval(REC_TICK_MS)
        self._rec_timer.timeout.connect(self._tick)

        self._build()
        self._scan()

    def _build(self) -> None:
        self._preview = Preview()

        self._camera = QComboBox()
        self._camera.setMinimumContentsLength(10)
        self._camera.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._camera.activated.connect(self._select_camera)
        self._scan_button = QPushButton("스캔")
        self._scan_button.clicked.connect(self._scan)
        camera_row = QHBoxLayout()
        camera_row.addWidget(self._camera, 1)
        camera_row.addWidget(self._scan_button)

        self._resolution = QComboBox()
        self._resolution.activated.connect(self._resolution_chosen)
        self._fps = QComboBox()
        self._fps.activated.connect(self._open_preview)
        self._label = QLineEdit()
        self._label.setPlaceholderText("예: trial_01 (선택)")
        self._root = QLineEdit(str(self._default_root))
        self._browse = QPushButton("…")
        self._browse.setFixedWidth(32)
        self._browse.clicked.connect(self._choose_root)
        root_row = QHBoxLayout()
        root_row.addWidget(self._root, 1)
        root_row.addWidget(self._browse)

        form = QFormLayout()
        form.addRow("카메라", camera_row)
        form.addRow("해상도", self._resolution)
        form.addRow("FPS", self._fps)
        form.addRow("라벨", self._label)
        form.addRow("저장 위치", root_row)

        self._record = QPushButton()
        self._record.clicked.connect(self._toggle_recording)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._record.click)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)

        panel = QVBoxLayout()
        panel.addLayout(form)
        panel.addWidget(self._record)
        panel.addWidget(self._log_view, 1)
        panel_widget = QWidget()
        panel_widget.setFixedWidth(PANEL_WIDTH)
        panel_widget.setLayout(panel)

        layout = QHBoxLayout()
        layout.addWidget(self._preview, 1)
        layout.addWidget(panel_widget)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.resize(1120, 560)
        self._update_controls()

    def _log(self, message: str) -> None:
        self._log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {message}")

    def _update_controls(self) -> None:
        locked = self._session is not None or self._transition
        for widget in (self._camera, self._scan_button, self._resolution, self._fps,
                       self._label, self._root, self._browse):
            widget.setEnabled(not locked)
        self._record.setEnabled(self._streaming and not self._transition)
        recording = self._session is not None
        self._record.setText("■ 녹화 중지 (Space)" if recording else "● 녹화 시작 (Space)")
        self._record.setStyleSheet(STOP_STYLE if recording else RECORD_STYLE)

    def _scan(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            devices, problems = scan()
        finally:
            QApplication.restoreOverrideCursor()
        for problem in problems:
            self._log(f"스캔 경고: {problem}")
        self._log(f"카메라 {len(devices)}대 발견")

        previous = self._device
        self._devices = devices
        self._camera.clear()
        self._camera.addItems([f"{device.name} ({device.detail})" for device in devices])
        if not devices:
            self._close_preview()
            self._device = None
            self._resolution.clear()
            self._fps.clear()
            self._preview.show_message("카메라를 찾지 못했습니다. 연결한 뒤 스캔을 누르세요.")
            self._update_controls()
            return

        same = [i for i, device in enumerate(devices) if previous and device.config == previous.config]
        self._camera.setCurrentIndex(same[0] if same else 0)
        if same and self._worker is not None:
            self._device = devices[same[0]]  # already previewing it: leave it running
        else:
            self._select_camera(self._camera.currentIndex())

    def _select_camera(self, index: int) -> None:
        self._device = self._devices[index]
        try:
            self._name, self._config = config_for(self._device)
        except (CameraError, OSError, KeyError, yaml.YAMLError) as e:
            self._close_preview()
            self._log(f"오류: 설정 파일을 읽지 못했습니다: {e}")
            self._update_controls()
            return
        self._fill_resolutions(self._default_mode())
        self._open_preview()

    def _default_mode(self) -> Mode | None:
        """Return the mode the config file asks for, else the largest one."""
        backend = load_backend(self._device.backend)
        for mode in self._device.modes:
            if backend.mode_config(mode).items() <= self._config.items():
                return mode
        return max(self._device.modes, default=None)

    def _fill_resolutions(self, mode: Mode | None) -> None:
        sizes = {(m.width, m.height) for m in self._device.modes}
        self._resolution.clear()
        for width, height in sorted(sizes, key=lambda size: size[0] * size[1], reverse=True):
            self._resolution.addItem(f"{width} x {height}", (width, height))
        if mode is not None:
            self._resolution.setCurrentText(f"{mode.width} x {mode.height}")
        self._fill_fps(mode.fps if mode else None)

    def _fill_fps(self, fps: float | None) -> None:
        self._fps.clear()
        if self._resolution.count() == 0:
            return
        width, height = self._resolution.currentData()
        rates = sorted(m.fps for m in self._device.modes if (m.width, m.height) == (width, height))
        for rate in rates:
            self._fps.addItem(f"{rate:g}", rate)
        self._fps.setCurrentText(f"{fps if fps in rates else rates[-1]:g}")

    def _resolution_chosen(self) -> None:
        self._fill_fps(self._fps.currentData())
        self._open_preview()

    def _selected_mode(self) -> Mode | None:
        if self._resolution.count() == 0:
            return None
        width, height = self._resolution.currentData()
        return Mode(width, height, self._fps.currentData())

    def _open_preview(self) -> None:
        self._close_preview()
        mode = self._selected_mode()
        if mode is None:
            message = f"{self._device.name}: 녹화할 수 있는 모드가 없습니다."
            self._preview.show_message(message)
            self._log(message)
            self._update_controls()
            return

        backend = load_backend(self._device.backend)
        config = {**self._config, **self._device.config, **backend.mode_config(mode)}
        self._preview.show_message("카메라 여는 중…")
        self._worker = CameraWorker(config, self._name, self)
        self._worker.opened.connect(self._on_opened)
        self._worker.frame.connect(self._on_frame)
        self._worker.recording_started.connect(self._on_recording_started)
        self._worker.recording_stopped.connect(self._on_recording_stopped)
        self._worker.recording_refused.connect(self._on_recording_refused)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()
        self._update_controls()

    def _close_preview(self) -> None:
        worker, self._worker = self._worker, None
        self._streaming = False
        if worker is not None:
            worker.shutdown()
            worker.wait()  # a stopped camera must be released before it is reopened
            worker.deleteLater()

    def _is_stale(self) -> bool:
        """A closed worker's last signals can arrive after a new one has started."""
        return self.sender() is not self._worker

    def _on_opened(self) -> None:
        if self._is_stale():
            return
        self._streaming = True
        self._log(f"미리보기: {self._name} {self._selected_mode()}")
        self._update_controls()

    def _on_frame(self, image: QImage) -> None:
        if not self._is_stale():
            self._preview.show_image(image)

    def _toggle_recording(self) -> None:
        self._transition = True
        if self._session is None:
            root = Path(self._root.text().strip() or self._default_root).expanduser()
            self._worker.begin_recording(root, self._label.text().strip() or None)
        else:
            self._worker.end_recording()
        self._update_controls()

    def _on_recording_started(self, session: Session) -> None:
        if self._is_stale():
            return
        self._session = session
        self._transition = False
        self._rec_timer.start()
        self._tick()
        self._log(f"녹화 시작: {session.path}")
        self._update_controls()

    def _tick(self) -> None:
        elapsed = int(time.monotonic() - self._session.monotonic_start)
        self._preview.set_overlay(f"● REC {elapsed // 60:02d}:{elapsed % 60:02d}")

    def _finish_recording(self) -> None:
        self._session = None
        self._transition = False
        self._rec_timer.stop()
        self._preview.set_overlay("")
        self._update_controls()

    def _on_recording_stopped(self, session: Session, stats: dict) -> None:
        if self._is_stale():
            return
        self._finish_recording()
        summary = ", ".join(f"{key}={stats[key]}" for key in STATS_SHOWN if key in stats)
        self._log(f"저장 완료: {session.path}\n{summary}")

    def _on_recording_refused(self, message: str) -> None:
        if self._is_stale():
            return
        self._finish_recording()
        self._log(f"녹화를 시작하지 못했습니다: {message}")

    def _on_failed(self, message: str) -> None:
        if self._is_stale():
            return
        self._close_preview()
        self._finish_recording()
        self._preview.show_message("카메라를 사용할 수 없습니다. 연결을 확인하고 스캔을 누르세요.")
        self._log(f"오류: {message}")

    def _choose_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "저장 위치", self._root.text())
        if folder:
            self._root.setText(folder)

    def closeEvent(self, event) -> None:
        if self._session is not None:
            answer = QMessageBox.question(self, "녹화 중", "녹화를 중지하고 종료할까요?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self._close_preview()  # the worker finishes any recording before it exits
        event.accept()


def _check_qt_platform() -> None:
    problem = qt_problem()
    if problem is None:
        return
    # Started from the app menu there is no terminal to read the error in.
    if not sys.stderr.isatty() and shutil.which("notify-send"):
        subprocess.run(["notify-send", "-i", "dialog-error", "Camera Recorder", problem], check=False)
    raise CameraError(problem)


def run(root: Path) -> None:
    _check_qt_platform()

    app = QApplication([APP_ID])
    app.setApplicationName(APP_ID)
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon(str(ICON)))
    app.setStyle("Fusion")
    window = MainWindow(root)
    window.show()

    # Ctrl+C in the terminal goes through closeEvent, so a recording is finished.
    # Python only runs signal handlers while Python code runs, hence the timer.
    signal.signal(signal.SIGINT, lambda *_: window.close())
    keep_python_awake = QTimer(window)
    keep_python_awake.timeout.connect(lambda: None)
    keep_python_awake.start(SIGNAL_POLL_MS)

    app.exec()
