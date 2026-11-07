"""Command line entry point: `camrec list` and `camrec record`."""

import argparse
import sys
from pathlib import Path

import yaml

from camera_recorder.cameras import BACKENDS, CameraError, load_backend
from camera_recorder.session import run

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"


def _load_config(ref: str) -> tuple[str, dict]:
    path = Path(ref) if ref.endswith((".yaml", ".yml")) else CONFIG_DIR / f"{ref}.yaml"
    if not path.is_file():
        raise CameraError(f"no config at {path} (see `camrec list`)")
    return path.stem, yaml.safe_load(path.read_text())


def _list() -> None:
    print("configs:")
    for path in sorted(CONFIG_DIR.glob("*.yaml")):
        print(f"  {path.stem}")
    for name in BACKENDS:
        print(f"{name} devices:")
        try:
            devices = load_backend(name).discover()
        except CameraError as e:
            print(f"  unavailable: {e}")
            continue
        for device in devices:
            print(f"  {device}")
        if not devices:
            print("  none")


def _record(args: argparse.Namespace) -> None:
    name, config = _load_config(args.camera)
    camera = load_backend(config["backend"])(config)
    run(
        camera,
        name,
        args.root,
        label=args.label,
        duration=args.duration,
        show_preview=not args.no_preview,
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="camrec", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="show configs and connected cameras")

    record = commands.add_parser("record", help="preview and record a camera")
    record.add_argument("camera", help="config name in configs/, or a path to a .yaml")
    record.add_argument("-l", "--label", help="added to the session folder name")
    record.add_argument("-d", "--duration", type=float, help="record now, stop after N seconds")
    record.add_argument("--no-preview", action="store_true", help="no window; record at once")
    record.add_argument("--root", type=Path, default=RECORDINGS_DIR, help="recordings folder")

    args = parser.parse_args()
    try:
        _list() if args.command == "list" else _record(args)
    except CameraError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
