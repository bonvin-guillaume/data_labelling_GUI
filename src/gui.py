from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPainterPath, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .data_store import (
    LABEL_GHOST,
    LABEL_NON,
    LABEL_UNKNOWN,
    VALID_LABELS,
    ImageIndex,
    LabelSession,
    index_images,
)
from .export_csv import export_labels_csv


class LabelingMainWindow(QMainWindow):
    def __init__(self, data_root: Path, session_file: Path, output_csv: Path):
        super().__init__()
        self.setWindowTitle("GHOST-Aurora Labeling Tool")
        self.resize(1400, 900)

        self.index: ImageIndex = index_images(data_root)
        self.session = LabelSession(session_file, self.index.root_dir)
        self.default_output_csv = output_csv
        self.index_image_set = set(self.index.all_images)
        self.labeled_count = sum(
            1 for image_path in self.index.all_images if self.session.get_label(image_path) in VALID_LABELS
        )

        self.current_day: str | None = None
        self.current_images: list[str] = []
        self.current_index = 0
        self.base_pixmap: QPixmap | None = None
        self.logo_pixmap = self._load_logo_pixmap()
        self.setWindowIcon(QIcon(self.logo_pixmap))

        self._build_ui()
        self._build_shortcuts()
        self._refresh_day_list()
        self._select_initial_day()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Days"))
        self.day_list = QListWidget()
        self.day_list.currentItemChanged.connect(self._on_day_changed)
        left_layout.addWidget(self.day_list)

        self.unlabeled_only_box = QCheckBox("Show only unlabeled images")
        self.unlabeled_only_box.toggled.connect(self._on_filter_changed)
        left_layout.addWidget(self.unlabeled_only_box)

        left_layout.addWidget(QLabel("Files in selected day"))
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.currentItemChanged.connect(self._on_file_changed)
        left_layout.addWidget(self.file_list, stretch=1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.logo_label.setPixmap(
            self.logo_pixmap.scaled(
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        right_layout.addWidget(self.logo_label)

        self.file_label = QLabel("No image selected")
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        right_layout.addWidget(self.file_label)

        self.label_label = QLabel("Label: (none)")
        right_layout.addWidget(self.label_label)

        self.image_label = QLabel("Load a day to begin")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_label.setStyleSheet("background-color: #1e1e1e; color: #c0c0c0;")
        right_layout.addWidget(self.image_label, stretch=1)

        controls = QHBoxLayout()
        self.prev_button = QPushButton("Previous [Left]")
        self.prev_button.clicked.connect(self.previous_image)
        controls.addWidget(self.prev_button)

        self.next_button = QPushButton("Next [Right]")
        self.next_button.clicked.connect(self.next_image)
        controls.addWidget(self.next_button)

        self.non_button = QPushButton("Label Non-GHOST [1]")
        self.non_button.clicked.connect(lambda: self.apply_label(LABEL_NON))
        controls.addWidget(self.non_button)

        self.ghost_button = QPushButton("Label GHOST [2]")
        self.ghost_button.clicked.connect(lambda: self.apply_label(LABEL_GHOST))
        controls.addWidget(self.ghost_button)

        self.unknown_button = QPushButton("Label Unknown [3]")
        self.unknown_button.clicked.connect(lambda: self.apply_label(LABEL_UNKNOWN))
        controls.addWidget(self.unknown_button)

        self.unlabel_button = QPushButton("Unlabel [U]")
        self.unlabel_button.clicked.connect(self.unlabel_current)
        controls.addWidget(self.unlabel_button)

        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_csv)
        controls.addWidget(self.export_button)

        right_layout.addLayout(controls)
        splitter.addWidget(right)
        splitter.setSizes([340, 1060])

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Left"), self, activated=self.previous_image)
        QShortcut(QKeySequence("Right"), self, activated=self.next_image)
        QShortcut(QKeySequence("1"), self, activated=lambda: self.apply_label(LABEL_NON))
        QShortcut(QKeySequence("2"), self, activated=lambda: self.apply_label(LABEL_GHOST))
        QShortcut(QKeySequence("3"), self, activated=lambda: self.apply_label(LABEL_UNKNOWN))
        QShortcut(QKeySequence("U"), self, activated=self.unlabel_current)

    def _refresh_day_list(self) -> None:
        selected_day = self.current_day
        self.day_list.clear()
        for day in self.index.days:
            total = len(self.index.by_day[day])
            labeled = self._day_labeled_count(day)
            text = f"{day} ({labeled}/{total})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, day)
            self.day_list.addItem(item)

        if selected_day:
            for idx in range(self.day_list.count()):
                item = self.day_list.item(idx)
                if item.data(Qt.ItemDataRole.UserRole) == selected_day:
                    self.day_list.setCurrentItem(item)
                    return

    def _select_initial_day(self) -> None:
        if self.day_list.count() == 0:
            return

        best_day_index = 0
        for idx, day in enumerate(self.index.days):
            if self._day_labeled_count(day) < len(self.index.by_day[day]):
                best_day_index = idx
                break
        self.day_list.setCurrentRow(best_day_index)

    def _day_labeled_count(self, day: str) -> int:
        return sum(1 for path in self.index.by_day[day] if self.session.get_label(path) in VALID_LABELS)

    def _visible_images(self, day: str) -> list[str]:
        paths = self.index.by_day[day]
        if not self.unlabeled_only_box.isChecked():
            return paths
        return [path for path in paths if self.session.get_label(path) is None]

    def _on_day_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        day = current.data(Qt.ItemDataRole.UserRole)
        self._select_day(day, preferred_path=None)

    def _on_filter_changed(self, _checked: bool) -> None:
        if not self.current_day:
            return
        current_path = self.current_images[self.current_index] if self.current_images else None
        self._select_day(self.current_day, preferred_path=current_path)

    def _select_day(self, day: str, preferred_path: str | None) -> None:
        self.current_day = day
        self.current_images = self._visible_images(day)

        if not self.current_images:
            self.current_index = 0
            self._render_empty_day(day)
            self._refresh_file_list(preferred_path=None)
            self._refresh_progress()
            return

        self._refresh_file_list(preferred_path=preferred_path)
        self._refresh_progress()

    def _refresh_file_list(self, preferred_path: str | None, preferred_paths: list[str] | None = None) -> None:
        self.file_list.blockSignals(True)
        self.file_list.clear()

        for image_path in self.current_images:
            label = self.session.get_label(image_path)
            file_name = Path(image_path).name
            if label == LABEL_GHOST:
                text = f"[G] {file_name}"
            elif label == LABEL_NON:
                text = f"[N] {file_name}"
            elif label == LABEL_UNKNOWN:
                text = f"[?] {file_name}"
            else:
                text = f"[ ] {file_name}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, image_path)
            item.setToolTip(image_path)
            self.file_list.addItem(item)

        if not self.current_images:
            self.file_list.blockSignals(False)
            return

        selected_paths = [path for path in (preferred_paths or []) if path in self.current_images]
        if selected_paths:
            selection_model = self.file_list.selectionModel()
            for path in selected_paths:
                row = self.current_images.index(path)
                model_index = self.file_list.model().index(row, 0)
                selection_model.select(model_index, QItemSelectionModel.SelectionFlag.Select)

        if preferred_path and preferred_path in self.current_images:
            selected_index = self.current_images.index(preferred_path)
        elif selected_paths:
            selected_index = self.current_images.index(selected_paths[0])
        else:
            selected_index = min(self.current_index, len(self.current_images) - 1)

        selection_model = self.file_list.selectionModel()
        current_model_index = self.file_list.model().index(selected_index, 0)
        selection_model.setCurrentIndex(current_model_index, QItemSelectionModel.SelectionFlag.NoUpdate)
        if not selected_paths:
            selection_model.select(current_model_index, QItemSelectionModel.SelectionFlag.Select)

        self.current_index = selected_index
        self.file_list.blockSignals(False)
        self._load_current_image()

    def _on_file_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None or not self.current_images:
            return
        selected_path = current.data(Qt.ItemDataRole.UserRole)
        if selected_path not in self.current_images:
            return
        self.current_index = self.current_images.index(selected_path)
        self._load_current_image()
        self._refresh_progress()

    def _render_empty_day(self, day: str) -> None:
        self.file_label.setText(f"{day}: no images matching current filter")
        self.label_label.setText("Label: (none)")
        self.base_pixmap = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("No images to display")

    def _load_current_image(self) -> None:
        if not self.current_images:
            self._render_empty_day(self.current_day or "")
            return

        image_path = self.current_images[self.current_index]
        self.file_label.setText(image_path)
        label = self.session.get_label(image_path)
        self.label_label.setText(f"Label: {label if label else '(none)'}")

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.base_pixmap = None
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText(f"Failed to load image: {image_path}")
            return

        self.base_pixmap = pixmap
        self.image_label.setText("")
        self._rescale_displayed_pixmap()

    def _rescale_displayed_pixmap(self) -> None:
        if self.base_pixmap is None:
            return
        target = self.image_label.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        scaled = self.base_pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale_displayed_pixmap()

    def previous_image(self) -> None:
        if not self.current_images:
            return
        self.file_list.setCurrentRow(max(0, self.current_index - 1))

    def next_image(self) -> None:
        if not self.current_images:
            return
        self.file_list.setCurrentRow(min(len(self.current_images) - 1, self.current_index + 1))

    def apply_label(self, label: str) -> None:
        if not self.current_images:
            return

        selected_paths = self._selected_image_paths()
        if len(selected_paths) > 1:
            self._apply_label_bulk(selected_paths, label)
            return

        image_path = selected_paths[0] if selected_paths else self.current_images[self.current_index]
        if image_path in self.current_images:
            self.current_index = self.current_images.index(image_path)
        previous_label = self.session.get_label(image_path)
        self.session.set_label(image_path, label)
        self._update_labeled_count(previous_label, label)
        self._refresh_day_list()
        self.current_images = self._visible_images(self.current_day)

        if self.unlabeled_only_box.isChecked():
            if not self.current_images:
                self._render_empty_day(self.current_day or "")
                self._refresh_file_list(preferred_path=None)
            else:
                next_index = min(self.current_index, len(self.current_images) - 1)
                self._refresh_file_list(preferred_path=self.current_images[next_index])
        else:
            self._refresh_file_list(preferred_path=image_path)

        self._refresh_progress()

    def unlabel_current(self) -> None:
        if not self.current_images:
            return

        selected_paths = self._selected_image_paths()
        if len(selected_paths) > 1:
            self._unlabel_bulk(selected_paths)
            return

        image_path = selected_paths[0] if selected_paths else self.current_images[self.current_index]
        if image_path in self.current_images:
            self.current_index = self.current_images.index(image_path)
        previous_label = self.session.get_label(image_path)
        self.session.unlabel(image_path)
        self._update_labeled_count(previous_label, None)
        self._refresh_day_list()
        self.current_images = self._visible_images(self.current_day)
        if not self.current_images:
            self._render_empty_day(self.current_day or "")
            self._refresh_file_list(preferred_path=None)
        else:
            self._refresh_file_list(preferred_path=image_path)
        self._refresh_progress()

    def _unlabel_bulk(self, selected_paths: list[str]) -> None:
        if not selected_paths:
            return

        previous_labels = {path: self.session.get_label(path) for path in selected_paths}
        paths_to_unlabel = [path for path in selected_paths if previous_labels[path] in VALID_LABELS]
        if paths_to_unlabel:
            self.session.unlabel_bulk(paths_to_unlabel)
            for path in paths_to_unlabel:
                self._update_labeled_count(previous_labels[path], None)

        self._refresh_day_list()
        self.current_images = self._visible_images(self.current_day)

        if not self.current_images:
            self._render_empty_day(self.current_day or "")
            self._refresh_file_list(preferred_path=None, preferred_paths=None)
            self._refresh_progress()
            return

        visible_selected_paths = [path for path in selected_paths if path in self.current_images]
        if visible_selected_paths:
            preferred_path = visible_selected_paths[0]
            preferred_paths = visible_selected_paths
        else:
            fallback_index = min(self.current_index, len(self.current_images) - 1)
            preferred_path = self.current_images[fallback_index]
            preferred_paths = None

        self._refresh_file_list(preferred_path=preferred_path, preferred_paths=preferred_paths)
        self._refresh_progress()

    def _selected_image_paths(self) -> list[str]:
        rows = sorted(
            {
                self.file_list.row(item)
                for item in self.file_list.selectedItems()
                if self.file_list.row(item) >= 0
            }
        )
        selected_paths = [self.current_images[row] for row in rows if row < len(self.current_images)]
        if selected_paths:
            return selected_paths
        if self.current_images:
            return [self.current_images[self.current_index]]
        return []

    def _apply_label_bulk(self, selected_paths: list[str], label: str) -> None:
        if not selected_paths:
            return
        if not self._confirm_bulk_overwrite(selected_paths):
            return

        previous_labels = {path: self.session.get_label(path) for path in selected_paths}
        updates = {
            path: label
            for path in selected_paths
            if previous_labels[path] != label
        }
        if updates:
            self.session.set_labels_bulk(updates)
            for path, new_label in updates.items():
                self._update_labeled_count(previous_labels[path], new_label)

        self._refresh_day_list()
        self.current_images = self._visible_images(self.current_day)

        if not self.current_images:
            self._render_empty_day(self.current_day or "")
            self._refresh_file_list(preferred_path=None, preferred_paths=None)
            self._refresh_progress()
            return

        visible_selected_paths = [path for path in selected_paths if path in self.current_images]
        if visible_selected_paths:
            preferred_path = visible_selected_paths[0]
            preferred_paths = visible_selected_paths
        else:
            fallback_index = min(self.current_index, len(self.current_images) - 1)
            preferred_path = self.current_images[fallback_index]
            preferred_paths = None

        self._refresh_file_list(preferred_path=preferred_path, preferred_paths=preferred_paths)
        self._refresh_progress()

    def _confirm_bulk_overwrite(self, selected_paths: list[str]) -> bool:
        labeled_count = sum(
            1 for path in selected_paths if self.session.get_label(path) in VALID_LABELS
        )
        if labeled_count == 0:
            return True
        message = (
            f"{len(selected_paths)} images selected.\n"
            f"{labeled_count} already have a label.\n\n"
            "Do you want to overwrite existing labels for this bulk action?"
        )
        choice = QMessageBox.question(
            self,
            "Confirm bulk overwrite",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return choice == QMessageBox.StandardButton.Yes

    def _refresh_progress(self) -> None:
        total = len(self.index.all_images)
        remaining = total - self.labeled_count
        self.statusBar().showMessage(f"Labeled {self.labeled_count}/{total} | Remaining {remaining}")

    def _update_labeled_count(self, previous_label: str | None, new_label: str | None) -> None:
        was_labeled = previous_label in VALID_LABELS
        is_labeled = new_label in VALID_LABELS
        if not was_labeled and is_labeled:
            self.labeled_count += 1
        elif was_labeled and not is_labeled:
            self.labeled_count -= 1

    def export_csv(self) -> None:
        suggested = str(self.default_output_csv.expanduser().resolve())
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export labels to CSV",
            suggested,
            "CSV files (*.csv)",
        )
        if not selected:
            return

        current_labels = {
            path: label
            for path, label in self.session.labels.items()
            if path in self.index_image_set
        }
        count = export_labels_csv(current_labels, Path(selected))
        skipped = len(self.session.labels) - len(current_labels)
        details = f"Exported {count} labeled images to:\n{selected}"
        if skipped > 0:
            details += f"\n\nSkipped {skipped} labels not in current indexed dataset."
        QMessageBox.information(
            self,
            "Export complete",
            details,
        )


    def _load_logo_pixmap(self) -> QPixmap:
        project_logo = Path(__file__).resolve().parent.parent / "labelling_app.png"
        logo = QPixmap(str(project_logo))
        if logo.isNull():
            logo = self._fallback_logo_pixmap()
        return self._rounded_corners_pixmap(logo, radius=40)

    def _rounded_corners_pixmap(self, pixmap: QPixmap, radius: int) -> QPixmap:
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        rect = QRectF(0.0, 0.0, float(pixmap.width()), float(pixmap.height()))
        path.addRoundedRect(rect, float(radius), float(radius))
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    def _fallback_logo_pixmap(self) -> QPixmap:
        width, height = 420, 130
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#0f172a"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(0, 0, width, height, QColor("#0b1120"))
        painter.fillRect(0, height // 2 - 10, width, 20, QColor("#1d4ed8"))
        painter.setPen(QColor("#67e8f9"))
        painter.setFont(QFont("Helvetica", 42, QFont.Weight.Bold))
        painter.drawText(24, 78, "GHOST")
        painter.setPen(QColor("#e2e8f0"))
        painter.setFont(QFont("Helvetica", 24, QFont.Weight.DemiBold))
        painter.drawText(218, 78, "AURORA")
        painter.end()
        return pixmap


def run_app(data_root: Path, session_file: Path, output_csv: Path) -> int:
    app = QApplication(sys.argv)
    window = LabelingMainWindow(data_root=data_root, session_file=session_file, output_csv=output_csv)
    app.setWindowIcon(window.windowIcon())
    window.show()
    return app.exec()

