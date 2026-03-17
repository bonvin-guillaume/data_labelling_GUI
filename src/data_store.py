from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

LABEL_GHOST = "GHOST-aurora"
LABEL_NON = "non-GHOST-aurora"
VALID_LABELS = {LABEL_GHOST, LABEL_NON}
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True)
class ImageIndex:
    root_dir: Path
    days: list[str]
    by_day: dict[str, list[str]]
    all_images: list[str]


def index_images(root_dir: Path) -> ImageIndex:
    root_dir = root_dir.expanduser().resolve()
    if not root_dir.exists() or not root_dir.is_dir():
        raise FileNotFoundError(f"Data root not found or not a directory: {root_dir}")

    by_day = _index_day_folders(root_dir)

    days = sorted(by_day.keys())
    all_images: list[str] = []
    for day in days:
        all_images.extend(by_day[day])

    if not all_images:
        raise ValueError(
            f"No supported images found under {root_dir}. "
            f"Expected day folders with {sorted(SUPPORTED_EXTENSIONS)} images."
        )

    return ImageIndex(root_dir=root_dir, days=days, by_day=by_day, all_images=all_images)


def _index_day_folders(root_dir: Path) -> dict[str, list[str]]:
    """Index folders that directly contain images.

    Preferred mode is one-folder-per-day under root. If none are found, we
    fall back to recursively searching for leaf folders that directly contain
    images (useful for layouts like year/month/day).
    """
    by_day: dict[str, list[str]] = {}

    direct_day_dirs = sorted([p for p in root_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
    for day_dir in direct_day_dirs:
        images = _images_directly_in_dir(day_dir)
        if images:
            by_day[day_dir.name] = images

    if by_day:
        return by_day

    # Fallback: recursive discovery of folders that directly contain images.
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        if not filenames:
            continue
        path_obj = Path(dirpath)
        images = [
            str((path_obj / name).resolve())
            for name in sorted(filenames)
            if (path_obj / name).suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        if images:
            key = str(path_obj.relative_to(root_dir))
            by_day[key] = images

    return dict(sorted(by_day.items(), key=lambda item: item[0]))


def _images_directly_in_dir(directory: Path) -> list[str]:
    return [
        str(path.resolve())
        for path in sorted(directory.iterdir(), key=lambda p: p.name)
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


class LabelSession:
    def __init__(self, session_path: Path, root_dir: Path):
        self.session_path = session_path.expanduser().resolve()
        self.root_dir = root_dir.expanduser().resolve()
        self.labels: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.session_path.exists():
            return

        with self.session_path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        labels = raw.get("labels", {})
        if not isinstance(labels, dict):
            return

        cleaned: dict[str, str] = {}
        for file_path, label in labels.items():
            if isinstance(file_path, str) and label in VALID_LABELS:
                cleaned[file_path] = label
        self.labels = cleaned

    def save(self) -> None:
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "root_dir": str(self.root_dir),
            "labels": self.labels,
        }
        with self.session_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def get_label(self, image_path: str) -> str | None:
        return self.labels.get(image_path)

    def set_label(self, image_path: str, label: str) -> None:
        if label not in VALID_LABELS:
            raise ValueError(f"Invalid label: {label}")
        self.labels[image_path] = label
        self.save()

    def unlabel(self, image_path: str) -> None:
        if image_path in self.labels:
            del self.labels[image_path]
            self.save()

