from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.gui import run_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GHOST-aurora image labeling GUI")
    parser.add_argument(
        "--data-root",
        required=True,
        type=str,
        help="Local root directory containing day folders (or nested year/month/day folders).",
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        default=Path(".ghost_label_session.json"),
        help="Path to session JSON used for autosave/resume.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("ghost_aurora_labels.csv"),
        help="Default CSV path used by the export dialog.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.data_root.lower().startswith("smb://"):
        raise SystemExit(
            "Use a mounted local path, not an smb:// URL.\n"
            "Example:\n"
            "  1) Mount the share in Finder (Go -> Connect to Server)\n"
            "  2) Run with a local mounted path, e.g. /Volumes/KHO/Sony/2024/12\n"
        )

    data_root = Path(args.data_root).expanduser().resolve()
    session_file = args.session_file.expanduser().resolve()
    output_csv = args.output_csv.expanduser().resolve()
    return run_app(
        data_root=data_root,
        session_file=session_file,
        output_csv=output_csv,
    )


if __name__ == "__main__":
    raise SystemExit(main())

