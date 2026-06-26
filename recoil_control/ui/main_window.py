"""Main application window: wires model, engine, listeners and widgets."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import Qt, QObject, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..engine import RecoilEngine
from ..input_backend import InputListener, IS_WINDOWS
from ..model import (
    ACTIVATION_LABELS,
    ACTIVATION_MODES,
    AppConfig,
    Profile,
    Step,
    config_path,
    load_config,
    save_config,
)
from . import style
from .pattern_canvas import PatternCanvas


class Bridge(QObject):
    """Marshals callbacks from worker/listener threads to the GUI thread."""

    status = Signal(bool, int)
    hotkey = Signal()


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__}")
        self.resize(1180, 720)

        self.cfg: AppConfig = load_config()
        self._loading = False

        self.bridge = Bridge()
        self.bridge.status.connect(self._on_status)
        self.bridge.hotkey.connect(self._toggle_master)

        self.engine = RecoilEngine(
            status_callback=lambda active, step: self.bridge.status.emit(active, step)
        )
        self.listener = InputListener(
            on_left=lambda pressed: self.engine.set_button(left=pressed),
            on_right=lambda pressed: self.engine.set_button(right=pressed),
            on_hotkey=lambda: self.bridge.hotkey.emit(),
        )

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_now)

        self._anim_timer = QTimer(self)
        self._anim_timer.setSingleShot(True)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_index = 0

        self._build_ui()
        self._refresh_profile_list()
        self._load_active_into_ui()

        # Push initial state to engine.
        self.cfg.master_enabled = False  # always start disarmed for safety
        self.engine.set_global_sensitivity(self.cfg.global_sensitivity)
        self.engine.set_active_profile(self.cfg.active_profile())
        self.listener.set_hotkey(self.cfg.toggle_hotkey)
        self.engine.start()
        try:
            self.listener.start()
        except Exception as exc:  # listener needs an input system; degrade gracefully
            self.subtitle.setText(f"Input listener unavailable: {exc}")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        body = QSplitter(Qt.Horizontal)
        body.setContentsMargins(12, 12, 12, 12)
        body.setHandleWidth(10)
        body.addWidget(self._build_left_panel())
        body.addWidget(self._build_center_panel())
        body.addWidget(self._build_right_panel())
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setStretchFactor(2, 0)
        body.setSizes([260, 600, 320])

        wrap = QWidget()
        wrap.setObjectName("root")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(12, 12, 12, 12)
        wl.addWidget(body)
        outer.addWidget(wrap, 1)

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 12, 16, 12)
        h.setSpacing(14)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel(__app_name__)
        title.setObjectName("title")
        self.subtitle = QLabel(
            f"v{__version__}  ·  {'Windows native input' if IS_WINDOWS else 'Dev mode (pynput input)'}"
        )
        self.subtitle.setObjectName("subtitle")
        titles.addWidget(title)
        titles.addWidget(self.subtitle)
        h.addLayout(titles)
        h.addStretch(1)

        self.status_pill = QLabel("OFF")
        self.status_pill.setObjectName("statusPill")
        h.addWidget(self.status_pill)

        hk_label = QLabel("Toggle hotkey")
        hk_label.setObjectName("subtitle")
        h.addWidget(hk_label)
        self.hotkey_edit = QLineEdit(self.cfg.toggle_hotkey)
        self.hotkey_edit.setFixedWidth(70)
        self.hotkey_edit.setAlignment(Qt.AlignCenter)
        self.hotkey_edit.editingFinished.connect(self._on_hotkey_changed)
        h.addWidget(self.hotkey_edit)

        gs_label = QLabel("Global sens")
        gs_label.setObjectName("subtitle")
        h.addWidget(gs_label)
        self.global_sens = QDoubleSpinBox()
        self.global_sens.setRange(0.05, 10.0)
        self.global_sens.setSingleStep(0.05)
        self.global_sens.setDecimals(2)
        self.global_sens.setValue(self.cfg.global_sensitivity)
        self.global_sens.setFixedWidth(80)
        self.global_sens.valueChanged.connect(self._on_global_sens)
        h.addWidget(self.global_sens)

        self.master_btn = QPushButton("ARM  (OFF)")
        self.master_btn.setObjectName("master")
        self.master_btn.setCheckable(True)
        self.master_btn.setChecked(False)
        self.master_btn.toggled.connect(self._on_master_toggled)
        h.addWidget(self.master_btn)

        return header

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)
        v.addWidget(_section("Weapon profiles"))

        self.profile_list = QListWidget()
        self.profile_list.currentRowChanged.connect(self._on_profile_selected)
        v.addWidget(self.profile_list, 1)

        row = QHBoxLayout()
        add = QPushButton("Add")
        add.clicked.connect(self._add_profile)
        dup = QPushButton("Duplicate")
        dup.clicked.connect(self._duplicate_profile)
        rem = QPushButton("Delete")
        rem.setObjectName("danger")
        rem.clicked.connect(self._delete_profile)
        row.addWidget(add)
        row.addWidget(dup)
        row.addWidget(rem)
        v.addLayout(row)

        row2 = QHBoxLayout()
        imp = QPushButton("Import…")
        imp.clicked.connect(self._import_profile)
        exp = QPushButton("Export…")
        exp.clicked.connect(self._export_profile)
        row2.addWidget(imp)
        row2.addWidget(exp)
        v.addLayout(row2)

        loc = QLabel(f"Profiles saved next to the app:\n{config_path().name}")
        loc.setObjectName("subtitle")
        loc.setWordWrap(True)
        v.addWidget(loc)
        return panel

    def _build_center_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(_section("Recoil pattern"))
        top.addStretch(1)
        zlabel = QLabel("Zoom")
        zlabel.setObjectName("subtitle")
        top.addWidget(zlabel)
        self.zoom = QSpinBox()
        self.zoom.setRange(2, 30)
        self.zoom.setValue(6)
        self.zoom.setSuffix(" px")
        self.zoom.valueChanged.connect(lambda val: self.canvas.set_scale(float(val)))
        top.addWidget(self.zoom)
        self.anim_btn = QPushButton("▶ Preview")
        self.anim_btn.clicked.connect(self._toggle_anim)
        top.addWidget(self.anim_btn)
        clear = QPushButton("Clear")
        clear.setObjectName("danger")
        clear.clicked.connect(self._clear_points)
        top.addWidget(clear)
        v.addLayout(top)

        self.canvas = PatternCanvas()
        self.canvas.changed.connect(self._on_canvas_changed)
        self.canvas.pointSelected.connect(self._on_canvas_point_selected)
        v.addWidget(self.canvas, 1)

        srow = QHBoxLayout()
        srow.addWidget(_section("Steps"))
        srow.addStretch(1)
        adds = QPushButton("Add step")
        adds.clicked.connect(self._add_step)
        rems = QPushButton("Remove step")
        rems.setObjectName("danger")
        rems.clicked.connect(self._remove_step)
        srow.addWidget(adds)
        srow.addWidget(rems)
        v.addLayout(srow)

        self.steps_table = QTableWidget(0, 3)
        self.steps_table.setHorizontalHeaderLabels(["dx", "dy", "delay (ms)"])
        self.steps_table.verticalHeader().setDefaultSectionSize(26)
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.steps_table.setMaximumHeight(190)
        self.steps_table.itemChanged.connect(self._on_table_item_changed)
        self.steps_table.itemSelectionChanged.connect(self._on_table_selection)
        v.addWidget(self.steps_table)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)
        v.addWidget(_section("Profile settings"))

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(8)

        grid.addWidget(QLabel("Name"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_name_changed)
        grid.addWidget(self.name_edit, 0, 1)

        grid.addWidget(QLabel("Weapon"), 1, 0)
        self.weapon_edit = QLineEdit()
        self.weapon_edit.textEdited.connect(self._on_field_changed)
        grid.addWidget(self.weapon_edit, 1, 1)

        grid.addWidget(QLabel("Activation"), 2, 0)
        self.activation = QComboBox()
        for mode in ACTIVATION_MODES:
            self.activation.addItem(ACTIVATION_LABELS[mode], mode)
        self.activation.currentIndexChanged.connect(self._on_field_changed)
        grid.addWidget(self.activation, 2, 1)

        grid.addWidget(QLabel("Sensitivity"), 3, 0)
        self.prof_sens = QDoubleSpinBox()
        self.prof_sens.setRange(0.05, 10.0)
        self.prof_sens.setSingleStep(0.05)
        self.prof_sens.setDecimals(2)
        self.prof_sens.valueChanged.connect(self._on_field_changed)
        grid.addWidget(self.prof_sens, 3, 1)
        v.addLayout(grid)

        self.loop_chk = QCheckBox("Loop pattern while held")
        self.loop_chk.toggled.connect(self._on_field_changed)
        v.addWidget(self.loop_chk)
        self.repeat_chk = QCheckBox("Hold last step while held")
        self.repeat_chk.toggled.connect(self._on_field_changed)
        v.addWidget(self.repeat_chk)

        v.addWidget(_section("Notes"))
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(120)
        self.note_edit.textChanged.connect(self._on_note_changed)
        v.addWidget(self.note_edit)

        v.addStretch(1)
        help_lbl = QLabel(
            "Tip: positive dy moves aim down to counter upward recoil. "
            "Click on the canvas to add points, drag to adjust, right-click to delete."
        )
        help_lbl.setObjectName("subtitle")
        help_lbl.setWordWrap(True)
        v.addWidget(help_lbl)
        return panel

    # -------------------------------------------------------------- helpers
    def _current_profile(self) -> Optional[Profile]:
        return self.cfg.active_profile()

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _save_now(self) -> None:
        try:
            save_config(self.cfg)
        except OSError as exc:
            self.subtitle.setText(f"Save failed: {exc}")

    # ----------------------------------------------------------- list logic
    def _refresh_profile_list(self) -> None:
        self._loading = True
        self.profile_list.clear()
        for p in self.cfg.profiles:
            label = p.name if not p.weapon else f"{p.name}  ·  {p.weapon}"
            self.profile_list.addItem(QListWidgetItem(label))
        if 0 <= self.cfg.active_index < self.profile_list.count():
            self.profile_list.setCurrentRow(self.cfg.active_index)
        self._loading = False

    def _load_active_into_ui(self) -> None:
        profile = self._current_profile()
        self._loading = True
        if profile is None:
            self.name_edit.setText("")
            self.weapon_edit.setText("")
            self.note_edit.setPlainText("")
            self.canvas.set_profile(None)
            self.steps_table.setRowCount(0)
            self._loading = False
            return
        self.name_edit.setText(profile.name)
        self.weapon_edit.setText(profile.weapon)
        idx = self.activation.findData(profile.activation)
        self.activation.setCurrentIndex(max(0, idx))
        self.prof_sens.setValue(profile.sensitivity)
        self.loop_chk.setChecked(profile.loop)
        self.repeat_chk.setChecked(profile.repeat_last)
        self.note_edit.setPlainText(profile.note)
        self.canvas.set_profile(profile)
        self._loading = False
        self._refresh_steps_table()

    def _refresh_steps_table(self) -> None:
        profile = self._current_profile()
        self._loading = True
        self.steps_table.setRowCount(0)
        if profile is not None:
            for s in profile.steps:
                r = self.steps_table.rowCount()
                self.steps_table.insertRow(r)
                self.steps_table.setItem(r, 0, QTableWidgetItem(str(s.dx)))
                self.steps_table.setItem(r, 1, QTableWidgetItem(str(s.dy)))
                self.steps_table.setItem(r, 2, QTableWidgetItem(str(s.delay_ms)))
        self._loading = False

    # --------------------------------------------------------------- events
    def _on_profile_selected(self, row: int) -> None:
        if self._loading or row < 0:
            return
        self.cfg.active_index = row
        self.engine.set_active_profile(self.cfg.active_profile())
        self._load_active_into_ui()
        self._schedule_save()

    def _add_profile(self) -> None:
        self.cfg.profiles.append(Profile(name=f"Profile {len(self.cfg.profiles) + 1}"))
        self.cfg.active_index = len(self.cfg.profiles) - 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._schedule_save()

    def _duplicate_profile(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        clone = Profile.from_dict(profile.to_dict())
        clone.name = f"{profile.name} (copy)"
        self.cfg.profiles.insert(self.cfg.active_index + 1, clone)
        self.cfg.active_index += 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._schedule_save()

    def _delete_profile(self) -> None:
        if not self.cfg.profiles:
            return
        if QMessageBox.question(
            self, "Delete profile", "Delete the selected profile?"
        ) != QMessageBox.Yes:
            return
        del self.cfg.profiles[self.cfg.active_index]
        if not self.cfg.profiles:
            self.cfg.profiles.append(Profile(name="Profile 1"))
        self.cfg.active_index = max(0, min(self.cfg.active_index, len(self.cfg.profiles) - 1))
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._schedule_save()

    def _on_name_changed(self, text: str) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None:
            return
        profile.name = text
        item = self.profile_list.item(self.cfg.active_index)
        if item is not None:
            item.setText(text if not profile.weapon else f"{text}  ·  {profile.weapon}")
        self._schedule_save()

    def _on_field_changed(self, *args) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None:
            return
        profile.weapon = self.weapon_edit.text()
        profile.activation = self.activation.currentData()
        profile.sensitivity = self.prof_sens.value()
        profile.loop = self.loop_chk.isChecked()
        profile.repeat_last = self.repeat_chk.isChecked()
        item = self.profile_list.item(self.cfg.active_index)
        if item is not None:
            item.setText(
                profile.name if not profile.weapon else f"{profile.name}  ·  {profile.weapon}"
            )
        self._schedule_save()

    def _on_note_changed(self) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None:
            return
        profile.note = self.note_edit.toPlainText()
        self._schedule_save()

    def _on_canvas_changed(self) -> None:
        self._refresh_steps_table()
        self._schedule_save()

    def _on_canvas_point_selected(self, index: int) -> None:
        if index < 0:
            return
        self._loading = True
        self.steps_table.selectRow(index)
        self._loading = False

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None or item.row() >= len(profile.steps):
            return
        step = profile.steps[item.row()]
        try:
            value = float(item.text().replace(",", "."))
        except ValueError:
            self._refresh_steps_table()
            return
        if item.column() == 0:
            step.dx = round(value, 2)
        elif item.column() == 1:
            step.dy = round(value, 2)
        else:
            step.delay_ms = max(1, int(value))
        self.canvas.update()
        self._schedule_save()

    def _on_table_selection(self) -> None:
        if self._loading:
            return
        rows = self.steps_table.selectionModel().selectedRows()
        self.canvas.select(rows[0].row() if rows else -1)

    def _add_step(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        profile.steps.append(Step(0.0, 5.0, 30))
        self._refresh_steps_table()
        self.canvas.update()
        self._schedule_save()

    def _remove_step(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        rows = sorted((r.row() for r in self.steps_table.selectionModel().selectedRows()), reverse=True)
        if not rows and profile.steps:
            rows = [len(profile.steps) - 1]
        for r in rows:
            if 0 <= r < len(profile.steps):
                del profile.steps[r]
        self._refresh_steps_table()
        self.canvas.update()
        self._schedule_save()

    def _clear_points(self) -> None:
        self.canvas.clear_points()

    # ---------------------------------------------------------- header logic
    def _on_master_toggled(self, checked: bool) -> None:
        self.cfg.master_enabled = checked
        self.engine.set_master_enabled(checked)
        self.master_btn.setText("ARMED  (ON)" if checked else "ARM  (OFF)")
        self._update_pill(False)
        self._schedule_save()

    def _toggle_master(self) -> None:
        self.master_btn.toggle()

    def _on_hotkey_changed(self) -> None:
        text = self.hotkey_edit.text().strip().lower()
        self.cfg.toggle_hotkey = text
        self.listener.set_hotkey(text)
        self._schedule_save()

    def _on_global_sens(self, value: float) -> None:
        self.cfg.global_sensitivity = value
        self.engine.set_global_sensitivity(value)
        self._schedule_save()

    def _on_status(self, active: bool, step: int) -> None:
        self.canvas.set_marker(step if active else -1)
        self._update_pill(active)

    def _update_pill(self, firing: bool) -> None:
        if firing:
            self.status_pill.setText("● FIRING")
            self.status_pill.setObjectName("statusPillOn")
        elif self.cfg.master_enabled:
            self.status_pill.setText("ARMED")
            self.status_pill.setObjectName("statusPillOn")
        else:
            self.status_pill.setText("OFF")
            self.status_pill.setObjectName("statusPill")
        # Re-apply stylesheet for the changed objectName.
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    # -------------------------------------------------------- preview anim
    def _toggle_anim(self) -> None:
        if self._anim_timer.isActive():
            self._stop_anim()
            return
        profile = self._current_profile()
        if profile is None or not profile.steps:
            return
        self._anim_index = 0
        self.anim_btn.setText("■ Stop")
        self._anim_tick()

    def _anim_tick(self) -> None:
        profile = self._current_profile()
        if profile is None or not profile.steps:
            self._stop_anim()
            return
        if self._anim_index >= len(profile.steps):
            self._stop_anim()
            return
        self.canvas.set_marker(self._anim_index)
        delay = max(15, profile.steps[self._anim_index].delay_ms)
        self._anim_index += 1
        self._anim_timer.start(delay)

    def _stop_anim(self) -> None:
        self._anim_timer.stop()
        self.canvas.set_marker(-1)
        self.anim_btn.setText("▶ Preview")

    # ------------------------------------------------------------- file I/O
    def _import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import profile", "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            profile = Profile.from_dict(data)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        self.cfg.profiles.append(profile)
        self.cfg.active_index = len(self.cfg.profiles) - 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._schedule_save()

    def _export_profile(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        default = f"{profile.name or 'profile'}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export profile", default, "JSON files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(profile.to_dict(), fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    # --------------------------------------------------------------- close
    def closeEvent(self, event) -> None:
        try:
            self.engine.set_master_enabled(False)
            self.engine.stop()
            self.listener.stop()
            self._save_now()
        finally:
            super().closeEvent(event)


def run() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName(__app_name__)
    app.setStyleSheet(style.STYLESHEET)
    window = MainWindow()
    window.show()
    # Convenience: Esc disarms instantly.
    panic = QShortcut(QKeySequence(Qt.Key_Escape), window)
    panic.activated.connect(lambda: window.master_btn.setChecked(False))
    return app.exec()
