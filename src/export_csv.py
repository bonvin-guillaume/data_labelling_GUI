from __future__ import annotations

import csv
from pathlib import Path

from .data_store import VALID_LABELS


def export_labels_csv(labels: dict[str, str], output_path: Path) -> int:
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    valid_rows = [(path, label) for path, label in labels.items() if label in VALID_LABELS]
    valid_rows.sort(key=lambda item: item[0])

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["filepath", "label"])
        writer.writerows(valid_rows)

    return len(valid_rows)

