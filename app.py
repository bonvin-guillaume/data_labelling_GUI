from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

from src.gui import run_app


def _default_session_file_for_data_root(data_root: Path) -> Path:
    preferred = data_root / ".ghost_label_session.json"
    if os.access(data_root, os.W_OK):
        return preferred

    # Keep per-folder isolation for read-only mounts by mapping each root to a
    # deterministic, user-writable session file under the home directory.
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", data_root.name).strip("._-") or "data_root"
    digest = hashlib.sha1(str(data_root).encode("utf-8")).hexdigest()[:12]
    fallback_dir = Path.home() / ".ghost_label_sessions"
    return fallback_dir / f"{slug}_{digest}.json"


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
        default=None,
        help=(
            "Optional path to session JSON used for autosave/resume. "
            "If omitted, defaults to <data_root>/.ghost_label_session.json "
            "(or a writable per-folder fallback under ~/.ghost_label_sessions)."
        ),
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
    if args.session_file is not None:
        session_file = args.session_file.expanduser().resolve()
    else:
        session_file = _default_session_file_for_data_root(data_root).expanduser().resolve()
    output_csv = args.output_csv.expanduser().resolve()
    return run_app(
        data_root=data_root,
        session_file=session_file,
        output_csv=output_csv,
    )


if __name__ == "__main__":
    raise SystemExit(main())

