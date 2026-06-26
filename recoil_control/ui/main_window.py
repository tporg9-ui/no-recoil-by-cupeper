"""Main application window: wires model, engine, listeners and widgets."""

from __future__ import annotations

import json
from typing import Optional

from PySide6.QtCore import Qt, QObject, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
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
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..engine import RecoilEngine
from ..i18n import LANGUAGES, TR, t
from ..input_backend import InputListener, IS_WINDOWS
from ..model import (
    ACTIVATION_LMB,
    ACTIVATION_LMB_AND_RMB,
    ACTIVATION_MODES,
    ACTIVATION_RMB,
    WEAPON_TEMPLATES,
    AppConfig,
    Profile,
    Step,
    config_path,
    load_config,
    save_config,
    template_profile,
)
from . import style
from .pattern_canvas import PatternCanvas

_ACTIVATION_KEYS = {
    ACTIVATION_LMB: "act_lmb",
    ACTIVATION_RMB: "act_rmb",
    ACTIVATION_LMB_AND_RMB: "act_lmb_rmb",
}

ACCENT_PRESETS = [
    "#27d796",  # green
    "#5cc8ff",  # blue
    "#ff5c5c",  # red
    "#ffb454",  # orange
    "#b78bff",  # purple
    "#ff7ac6",  # pink
]


class Bridge(QObject):
    """Marshals callbacks from worker/listener threads to the GUI thread."""

    status = Signal(bool, int)
    hotkey = Signal()
    captured = Signal(str)
    switch = Signal(int)


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionTitle")
    return lbl


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__app_name__}")
        self.resize(1240, 760)

        self.cfg: AppConfig = load_config()
        TR.set_language(self.cfg.language)
        sheet = style.apply_theme(self.cfg.accent, self.cfg.theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(sheet)

        self._loading = False
        self._capturing: Optional[str] = None

        self.bridge = Bridge()
        self.bridge.status.connect(self._on_status)
        self.bridge.hotkey.connect(self._toggle_master)
        self.bridge.captured.connect(self._on_key_captured)
        self.bridge.switch.connect(self._switch_to_index)

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
        self._retranslate()

        # Push initial state to engine.
        self.cfg.master_enabled = False  # always start disarmed for safety
        self.engine.set_global_sensitivity(self.cfg.global_sensitivity)
        self.engine.set_active_profile(self.cfg.active_profile())
        self.listener.set_hotkey(self.cfg.toggle_hotkey)
        self._refresh_hotkeys()
        self.engine.start()
        try:
            self.listener.start()
        except Exception as exc:  # listener needs an input system; degrade gracefully
            self.subtitle.setText(t("input_unavailable", error=exc))

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
        body.setHandleWidth(10)
        body.addWidget(self._build_left_panel())
        body.addWidget(self._build_tabs())
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        body.setSizes([280, 920])

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
        self.lbl_profiles = _section("Weapon profiles")
        v.addWidget(self.lbl_profiles)

        self.profile_list = QListWidget()
        self.profile_list.currentRowChanged.connect(self._on_profile_selected)
        v.addWidget(self.profile_list, 1)

        row = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_profile)
        self.dup_btn = QPushButton("Duplicate")
        self.dup_btn.clicked.connect(self._duplicate_profile)
        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("danger")
        self.del_btn.clicked.connect(self._delete_profile)
        row.addWidget(self.add_btn)
        row.addWidget(self.dup_btn)
        row.addWidget(self.del_btn)
        v.addLayout(row)

        self.template_btn = QPushButton("New from template…")
        self.template_btn.setMenu(self._build_template_menu())
        v.addWidget(self.template_btn)

        row2 = QHBoxLayout()
        self.imp_btn = QPushButton("Import…")
        self.imp_btn.clicked.connect(self._import_profile)
        self.exp_btn = QPushButton("Export…")
        self.exp_btn.clicked.connect(self._export_profile)
        row2.addWidget(self.imp_btn)
        row2.addWidget(self.exp_btn)
        v.addLayout(row2)

        self.loc_lbl = QLabel("")
        self.loc_lbl.setObjectName("subtitle")
        self.loc_lbl.setWordWrap(True)
        v.addWidget(self.loc_lbl)
        return panel

    def _build_tabs(self) -> QWidget:
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_main_tab(), "Main")
        self.tabs.addTab(self._build_pattern_tab(), "Pattern")
        self.tabs.addTab(self._build_appearance_tab(), "Appearance")
        return self.tabs

    # ------------------------------------------------------------ main tab
    def _build_main_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        panel = QFrame()
        panel.setObjectName("panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        # --- Game / weapon quick selector (top-left) ----------------------
        bar = QHBoxLayout()
        bar.setSpacing(8)
        self.lbl_game = QLabel("Game")
        bar.addWidget(self.lbl_game)
        self.game_combo = QComboBox()
        self.game_combo.setMinimumWidth(140)
        self.game_combo.currentIndexChanged.connect(self._on_game_changed)
        bar.addWidget(self.game_combo)

        self.lbl_weapon_pick = QLabel("Weapon")
        bar.addWidget(self.lbl_weapon_pick)
        self.weapon_btn = QPushButton("—")
        self.weapon_btn.setMinimumWidth(200)
        self.weapon_menu = QMenu(self)
        self.weapon_btn.setMenu(self.weapon_menu)
        self.weapon_menu.aboutToShow.connect(self._rebuild_weapon_menu)
        bar.addWidget(self.weapon_btn, 1)
        bar.addStretch(1)
        v.addLayout(bar)

        # --- Profile settings --------------------------------------------
        self.lbl_profile_settings = _section("Profile settings")
        v.addWidget(self.lbl_profile_settings)

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(8)

        self.lbl_name = QLabel("Name")
        grid.addWidget(self.lbl_name, 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.textEdited.connect(self._on_name_changed)
        grid.addWidget(self.name_edit, 0, 1)

        self.lbl_weapon = QLabel("Weapon")
        grid.addWidget(self.lbl_weapon, 1, 0)
        self.weapon_edit = QLineEdit()
        self.weapon_edit.textEdited.connect(self._on_field_changed)
        grid.addWidget(self.weapon_edit, 1, 1)

        self.lbl_group = QLabel("Group")
        grid.addWidget(self.lbl_group, 2, 0)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(["", *WEAPON_TEMPLATES.keys()])
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        grid.addWidget(self.category_combo, 2, 1)

        self.lbl_activation = QLabel("Activation")
        grid.addWidget(self.lbl_activation, 3, 0)
        self.activation = QComboBox()
        for mode in ACTIVATION_MODES:
            self.activation.addItem(t(_ACTIVATION_KEYS[mode]), mode)
        self.activation.currentIndexChanged.connect(self._on_field_changed)
        grid.addWidget(self.activation, 3, 1)

        self.lbl_strength = QLabel("Compensation strength")
        grid.addWidget(self.lbl_strength, 4, 0)
        self.prof_sens = QDoubleSpinBox()
        self.prof_sens.setRange(0.05, 10.0)
        self.prof_sens.setSingleStep(0.05)
        self.prof_sens.setDecimals(2)
        self.prof_sens.valueChanged.connect(self._on_field_changed)
        grid.addWidget(self.prof_sens, 4, 1)

        self.lbl_game_sens = QLabel("In-game sensitivity")
        grid.addWidget(self.lbl_game_sens, 5, 0)
        self.game_sens = QDoubleSpinBox()
        self.game_sens.setRange(0.01, 100.0)
        self.game_sens.setSingleStep(0.05)
        self.game_sens.setDecimals(3)
        self.game_sens.valueChanged.connect(self._on_field_changed)
        grid.addWidget(self.game_sens, 5, 1)
        v.addLayout(grid)

        self.loop_chk = QCheckBox("Loop pattern while held")
        self.loop_chk.toggled.connect(self._on_field_changed)
        v.addWidget(self.loop_chk)
        self.repeat_chk = QCheckBox("Hold last step while held")
        self.repeat_chk.toggled.connect(self._on_field_changed)
        v.addWidget(self.repeat_chk)

        # --- Randomization ------------------------------------------------
        self.lbl_random = _section("Randomization")
        v.addWidget(self.lbl_random)
        self.random_chk = QCheckBox("Enable randomization (humanize)")
        self.random_chk.toggled.connect(self._on_field_changed)
        v.addWidget(self.random_chk)

        rgrid = QGridLayout()
        rgrid.setHorizontalSpacing(8)
        rgrid.setVerticalSpacing(8)
        self.lbl_pos_jitter = QLabel("Position jitter (px)")
        rgrid.addWidget(self.lbl_pos_jitter, 0, 0)
        self.rand_pos = QDoubleSpinBox()
        self.rand_pos.setRange(0.0, 50.0)
        self.rand_pos.setSingleStep(0.5)
        self.rand_pos.setDecimals(1)
        self.rand_pos.valueChanged.connect(self._on_field_changed)
        rgrid.addWidget(self.rand_pos, 0, 1)
        self.lbl_delay_jitter = QLabel("Delay jitter (ms)")
        rgrid.addWidget(self.lbl_delay_jitter, 1, 0)
        self.rand_delay = QSpinBox()
        self.rand_delay.setRange(0, 500)
        self.rand_delay.valueChanged.connect(self._on_field_changed)
        rgrid.addWidget(self.rand_delay, 1, 1)
        v.addLayout(rgrid)

        # --- Keybinds -----------------------------------------------------
        self.lbl_keybinds = _section("Keybinds")
        v.addWidget(self.lbl_keybinds)
        kgrid = QGridLayout()
        kgrid.setHorizontalSpacing(8)
        kgrid.setVerticalSpacing(8)
        self.lbl_macro_key = QLabel("Macro on/off key")
        kgrid.addWidget(self.lbl_macro_key, 0, 0)
        self.macro_key_btn = QPushButton("—")
        self.macro_key_btn.clicked.connect(lambda: self._bind_key("macro"))
        kgrid.addWidget(self.macro_key_btn, 0, 1)

        self.lbl_switch_key = QLabel("Switch-to-profile key")
        kgrid.addWidget(self.lbl_switch_key, 1, 0)
        self.switch_key_btn = QPushButton("—")
        self.switch_key_btn.clicked.connect(lambda: self._bind_key("switch"))
        kgrid.addWidget(self.switch_key_btn, 1, 1)
        self.switch_clear_btn = QPushButton("Clear")
        self.switch_clear_btn.clicked.connect(self._clear_switch_key)
        kgrid.addWidget(self.switch_clear_btn, 1, 2)
        v.addLayout(kgrid)

        # --- Notes --------------------------------------------------------
        self.lbl_notes = _section("Notes")
        v.addWidget(self.lbl_notes)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setMaximumHeight(110)
        self.note_edit.textChanged.connect(self._on_note_changed)
        v.addWidget(self.note_edit)

        self.tip_lbl = QLabel("")
        self.tip_lbl.setObjectName("subtitle")
        self.tip_lbl.setWordWrap(True)
        v.addWidget(self.tip_lbl)
        v.addStretch(1)

        scroll.setWidget(panel)
        return scroll

    # --------------------------------------------------------- pattern tab
    def _build_pattern_tab(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(8)

        top = QHBoxLayout()
        self.lbl_pattern = _section("Recoil pattern")
        top.addWidget(self.lbl_pattern)
        top.addStretch(1)
        self.lbl_zoom = QLabel("Zoom")
        self.lbl_zoom.setObjectName("subtitle")
        top.addWidget(self.lbl_zoom)
        self.zoom = QSpinBox()
        self.zoom.setRange(2, 30)
        self.zoom.setValue(6)
        self.zoom.setSuffix(" px")
        self.zoom.valueChanged.connect(lambda val: self.canvas.set_scale(float(val)))
        top.addWidget(self.zoom)
        self.anim_btn = QPushButton("▶ Preview")
        self.anim_btn.clicked.connect(self._toggle_anim)
        top.addWidget(self.anim_btn)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("danger")
        self.clear_btn.clicked.connect(self._clear_points)
        top.addWidget(self.clear_btn)
        v.addLayout(top)

        self.canvas = PatternCanvas()
        self.canvas.changed.connect(self._on_canvas_changed)
        self.canvas.pointSelected.connect(self._on_canvas_point_selected)
        v.addWidget(self.canvas, 1)

        srow = QHBoxLayout()
        self.lbl_steps = _section("Steps")
        srow.addWidget(self.lbl_steps)
        srow.addStretch(1)
        self.add_step_btn = QPushButton("Add step")
        self.add_step_btn.clicked.connect(self._add_step)
        self.rem_step_btn = QPushButton("Remove step")
        self.rem_step_btn.setObjectName("danger")
        self.rem_step_btn.clicked.connect(self._remove_step)
        srow.addWidget(self.add_step_btn)
        srow.addWidget(self.rem_step_btn)
        v.addLayout(srow)

        self.steps_table = QTableWidget(0, 3)
        self.steps_table.setHorizontalHeaderLabels(["dx", "dy", "delay (ms)"])
        self.steps_table.verticalHeader().setDefaultSectionSize(26)
        self.steps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.steps_table.setMaximumHeight(220)
        self.steps_table.itemChanged.connect(self._on_table_item_changed)
        self.steps_table.itemSelectionChanged.connect(self._on_table_selection)
        v.addWidget(self.steps_table)
        return panel

    # ------------------------------------------------------ appearance tab
    def _build_appearance_tab(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(14, 14, 14, 14)
        v.setSpacing(10)

        self.lbl_appearance = _section("Appearance & general")
        v.addWidget(self.lbl_appearance)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)

        self.lbl_language = QLabel("Language")
        grid.addWidget(self.lbl_language, 0, 0)
        self.lang_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.lang_combo.addItem(label, code)
        idx = self.lang_combo.findData(self.cfg.language)
        self.lang_combo.setCurrentIndex(max(0, idx))
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        grid.addWidget(self.lang_combo, 0, 1)

        self.lbl_theme = QLabel("Theme")
        grid.addWidget(self.lbl_theme, 1, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        tidx = self.theme_combo.findData(self.cfg.theme)
        self.theme_combo.setCurrentIndex(max(0, tidx))
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        grid.addWidget(self.theme_combo, 1, 1)

        self.lbl_accent = QLabel("Accent color")
        grid.addWidget(self.lbl_accent, 2, 0)
        accent_row = QHBoxLayout()
        accent_row.setSpacing(6)
        self._accent_btns: list[QPushButton] = []
        for color in ACCENT_PRESETS:
            btn = QPushButton()
            btn.setFixedSize(26, 26)
            btn.setStyleSheet(
                f"background:{color}; border:1px solid #00000044; border-radius:13px;"
            )
            btn.clicked.connect(lambda _c=False, col=color: self._set_accent(col))
            accent_row.addWidget(btn)
            self._accent_btns.append(btn)
        self.accent_pick_btn = QPushButton("Pick…")
        self.accent_pick_btn.clicked.connect(self._pick_accent)
        accent_row.addWidget(self.accent_pick_btn)
        accent_row.addStretch(1)
        accent_wrap = QWidget()
        accent_wrap.setLayout(accent_row)
        grid.addWidget(accent_wrap, 2, 1)

        self.lbl_global_sens = QLabel("Global sensitivity")
        grid.addWidget(self.lbl_global_sens, 3, 0)
        self.global_sens = QDoubleSpinBox()
        self.global_sens.setRange(0.05, 10.0)
        self.global_sens.setSingleStep(0.05)
        self.global_sens.setDecimals(2)
        self.global_sens.setValue(self.cfg.global_sensitivity)
        self.global_sens.valueChanged.connect(self._on_global_sens)
        grid.addWidget(self.global_sens, 3, 1)
        v.addLayout(grid)

        v.addStretch(1)
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
            self.subtitle.setText(t("save_failed", error=exc))

    # ----------------------------------------------------------- list logic
    def _profile_label(self, p: Profile) -> str:
        base = p.name if not p.weapon else f"{p.name}  ·  {p.weapon}"
        if p.switch_hotkey:
            base += f"  [{p.switch_hotkey}]"
        return base

    def _list_row_for_active(self) -> int:
        for row, pidx in enumerate(self._row_to_profile):
            if pidx == self.cfg.active_index:
                return row
        return -1

    def _refresh_profile_list(self) -> None:
        self._loading = True
        self.profile_list.clear()
        # Map each visible list row back to a profile index (-1 = header row).
        self._row_to_profile: list[int] = []

        groups: dict[str, list[int]] = {}
        order: list[str] = []
        for i, p in enumerate(self.cfg.profiles):
            cat = p.category.strip() or t("ungrouped")
            if cat not in groups:
                groups[cat] = []
                order.append(cat)
            groups[cat].append(i)

        for cat in order:
            header = QListWidgetItem(cat.upper())
            header.setFlags(Qt.NoItemFlags)
            self.profile_list.addItem(header)
            self._row_to_profile.append(-1)
            for i in groups[cat]:
                item = QListWidgetItem("    " + self._profile_label(self.cfg.profiles[i]))
                self.profile_list.addItem(item)
                self._row_to_profile.append(i)

        row = self._list_row_for_active()
        if row >= 0:
            self.profile_list.setCurrentRow(row)
        self._refresh_game_combo()
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
            self.weapon_btn.setText("—")
            self.macro_key_btn.setText(self.cfg.toggle_hotkey or t("click_to_bind"))
            self.switch_key_btn.setText(t("click_to_bind"))
            self._loading = False
            return
        self.name_edit.setText(profile.name)
        self.weapon_edit.setText(profile.weapon)
        self.category_combo.setCurrentText(profile.category)
        idx = self.activation.findData(profile.activation)
        self.activation.setCurrentIndex(max(0, idx))
        self.prof_sens.setValue(profile.sensitivity)
        self.game_sens.setValue(profile.game_sensitivity)
        self.loop_chk.setChecked(profile.loop)
        self.repeat_chk.setChecked(profile.repeat_last)
        self.random_chk.setChecked(profile.randomize)
        self.rand_pos.setValue(profile.rand_pos)
        self.rand_delay.setValue(profile.rand_delay)
        self.note_edit.setPlainText(profile.note)
        self.macro_key_btn.setText(self.cfg.toggle_hotkey or t("click_to_bind"))
        self._update_switch_btn()
        self.weapon_btn.setText(profile.weapon or profile.name or "—")
        self._sync_game_combo_to_active()
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

    # ------------------------------------------------------ game / weapon
    def _categories(self) -> list[str]:
        seen: list[str] = []
        for key in WEAPON_TEMPLATES:
            if key not in seen:
                seen.append(key)
        for p in self.cfg.profiles:
            cat = p.category.strip()
            if cat and cat not in seen:
                seen.append(cat)
        return seen

    def _refresh_game_combo(self) -> None:
        if not hasattr(self, "game_combo"):
            return
        prev = self.game_combo.currentData()
        self.game_combo.blockSignals(True)
        self.game_combo.clear()
        self.game_combo.addItem(t("all_games"), "")
        for cat in self._categories():
            self.game_combo.addItem(cat, cat)
        idx = self.game_combo.findData(prev)
        self.game_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.game_combo.blockSignals(False)

    def _sync_game_combo_to_active(self) -> None:
        profile = self._current_profile()
        if profile is None or not hasattr(self, "game_combo"):
            return
        cat = profile.category.strip()
        idx = self.game_combo.findData(cat) if cat else 0
        self.game_combo.blockSignals(True)
        self.game_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.game_combo.blockSignals(False)

    def _on_game_changed(self, _idx: int) -> None:
        # Selector only filters the weapon dropdown; no profile change here.
        self.weapon_btn.setText(self.weapon_btn.text())

    def _rebuild_weapon_menu(self) -> None:
        self.weapon_menu.clear()
        game = self.game_combo.currentData() if hasattr(self, "game_combo") else ""
        any_added = False
        for i, p in enumerate(self.cfg.profiles):
            if game and p.category.strip() != game:
                continue
            act = self.weapon_menu.addAction(self._profile_label(p))
            act.triggered.connect(lambda _c=False, idx=i: self._switch_to_index(idx))
            any_added = True
        if not any_added:
            act = self.weapon_menu.addAction(t("no_weapons"))
            act.setEnabled(False)

    def _switch_to_index(self, idx: int) -> None:
        if not (0 <= idx < len(self.cfg.profiles)):
            return
        self.cfg.active_index = idx
        self.engine.set_active_profile(self.cfg.active_profile())
        row = self._list_row_for_active()
        if row >= 0:
            self._loading = True
            self.profile_list.setCurrentRow(row)
            self._loading = False
        self._load_active_into_ui()
        self._schedule_save()

    # --------------------------------------------------------------- events
    def _on_profile_selected(self, row: int) -> None:
        if self._loading or row < 0 or row >= len(self._row_to_profile):
            return
        pidx = self._row_to_profile[row]
        if pidx < 0:  # header row
            return
        self.cfg.active_index = pidx
        self.engine.set_active_profile(self.cfg.active_profile())
        self._load_active_into_ui()
        self._schedule_save()

    def _add_profile(self) -> None:
        self.cfg.profiles.append(Profile(name=f"Profile {len(self.cfg.profiles) + 1}"))
        self.cfg.active_index = len(self.cfg.profiles) - 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._refresh_hotkeys()
        self._schedule_save()

    def _duplicate_profile(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        clone = Profile.from_dict(profile.to_dict())
        clone.name = f"{profile.name} (copy)"
        clone.switch_hotkey = ""  # avoid duplicate binds
        self.cfg.profiles.insert(self.cfg.active_index + 1, clone)
        self.cfg.active_index += 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._refresh_hotkeys()
        self._schedule_save()

    def _delete_profile(self) -> None:
        if not self.cfg.profiles:
            return
        if QMessageBox.question(
            self, t("delete_profile_title"), t("delete_profile_msg")
        ) != QMessageBox.Yes:
            return
        del self.cfg.profiles[self.cfg.active_index]
        if not self.cfg.profiles:
            self.cfg.profiles.append(Profile(name="Profile 1"))
        self.cfg.active_index = max(0, min(self.cfg.active_index, len(self.cfg.profiles) - 1))
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._refresh_hotkeys()
        self._schedule_save()

    def _on_name_changed(self, text: str) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None:
            return
        profile.name = text
        self._update_active_list_label()
        self._schedule_save()

    def _update_active_list_label(self) -> None:
        profile = self._current_profile()
        row = self._list_row_for_active()
        item = self.profile_list.item(row) if row >= 0 else None
        if profile is not None and item is not None:
            item.setText("    " + self._profile_label(profile))
        if profile is not None:
            self.weapon_btn.setText(profile.weapon or profile.name or "—")

    def _on_field_changed(self, *args) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None:
            return
        profile.weapon = self.weapon_edit.text()
        profile.activation = self.activation.currentData()
        profile.sensitivity = self.prof_sens.value()
        profile.game_sensitivity = self.game_sens.value()
        profile.loop = self.loop_chk.isChecked()
        profile.repeat_last = self.repeat_chk.isChecked()
        profile.randomize = self.random_chk.isChecked()
        profile.rand_pos = self.rand_pos.value()
        profile.rand_delay = self.rand_delay.value()
        self._update_active_list_label()
        self._schedule_save()

    def _on_category_changed(self, text: str) -> None:
        if self._loading:
            return
        profile = self._current_profile()
        if profile is None:
            return
        profile.category = text.strip()
        self._refresh_profile_list()
        self._schedule_save()

    # ----------------------------------------------------------- keybinds
    def _update_switch_btn(self) -> None:
        profile = self._current_profile()
        key = profile.switch_hotkey if profile else ""
        self.switch_key_btn.setText(key or t("click_to_bind"))

    def _bind_key(self, target: str) -> None:
        self._capturing = target
        btn = self.macro_key_btn if target == "macro" else self.switch_key_btn
        btn.setText(t("press_a_key"))
        self.listener.capture_next_key(lambda key: self.bridge.captured.emit(key))

    def _on_key_captured(self, key: str) -> None:
        target = self._capturing
        self._capturing = None
        if not key:
            self._load_active_into_ui()
            return
        if target == "macro":
            self.cfg.toggle_hotkey = key
            self.listener.set_hotkey(key)
            self.macro_key_btn.setText(key)
        elif target == "switch":
            profile = self._current_profile()
            if profile is not None:
                profile.switch_hotkey = key
                self._update_switch_btn()
                self._update_active_list_label()
                self._refresh_hotkeys()
        self._schedule_save()

    def _clear_switch_key(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        profile.switch_hotkey = ""
        self._update_switch_btn()
        self._update_active_list_label()
        self._refresh_hotkeys()
        self._schedule_save()

    def _refresh_hotkeys(self) -> None:
        mapping: dict[str, object] = {}
        for i, p in enumerate(self.cfg.profiles):
            key = p.switch_hotkey.strip().lower()
            if key and key != self.cfg.toggle_hotkey.strip().lower():
                mapping[key] = (lambda idx=i: self.bridge.switch.emit(idx))
        self.listener.set_extra_hotkeys(mapping)

    # -------------------------------------------------------- templates
    def _build_template_menu(self) -> QMenu:
        menu = QMenu(self)
        for category, weapons in WEAPON_TEMPLATES.items():
            sub = menu.addMenu(category)
            all_act = sub.addAction(t("add_all_slots", category=category))
            all_act.triggered.connect(
                lambda _checked=False, c=category: self._add_template_group(c)
            )
            sub.addSeparator()
            for weapon in weapons:
                act = sub.addAction(weapon)
                act.triggered.connect(
                    lambda _checked=False, c=category, w=weapon: self._add_template_slot(c, w)
                )
        return menu

    def _add_template_slot(self, category: str, weapon: str) -> None:
        self.cfg.profiles.append(template_profile(category, weapon))
        self.cfg.active_index = len(self.cfg.profiles) - 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._schedule_save()

    def _add_template_group(self, category: str) -> None:
        for weapon in WEAPON_TEMPLATES.get(category, []):
            self.cfg.profiles.append(template_profile(category, weapon))
        self.cfg.active_index = len(self.cfg.profiles) - 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
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
        self.master_btn.setText(t("armed_on") if checked else t("arm_off"))
        self._update_pill(False)
        self._schedule_save()

    def _toggle_master(self) -> None:
        self.master_btn.toggle()

    def _on_global_sens(self, value: float) -> None:
        self.cfg.global_sensitivity = value
        self.engine.set_global_sensitivity(value)
        self._schedule_save()

    def _on_status(self, active: bool, step: int) -> None:
        self.canvas.set_marker(step if active else -1)
        self._update_pill(active)

    def _update_pill(self, firing: bool) -> None:
        if firing:
            self.status_pill.setText(t("status_firing"))
            self.status_pill.setObjectName("statusPillOn")
        elif self.cfg.master_enabled:
            self.status_pill.setText(t("status_armed"))
            self.status_pill.setObjectName("statusPillOn")
        else:
            self.status_pill.setText(t("status_off"))
            self.status_pill.setObjectName("statusPill")
        # Re-apply stylesheet for the changed objectName.
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    # --------------------------------------------------- appearance logic
    def _on_language_changed(self, _idx: int) -> None:
        code = self.lang_combo.currentData()
        self.cfg.language = code
        TR.set_language(code)
        self._retranslate()
        self._schedule_save()

    def _on_theme_changed(self, _idx: int) -> None:
        self.cfg.theme = self.theme_combo.currentData()
        self._apply_theme()
        self._schedule_save()

    def _set_accent(self, color: str) -> None:
        self.cfg.accent = color
        self._apply_theme()
        self._schedule_save()

    def _pick_accent(self) -> None:
        initial = QColor(self.cfg.accent)
        color = QColorDialog.getColor(initial, self, t("accent_color"))
        if color.isValid():
            self._set_accent(color.name())

    def _apply_theme(self) -> None:
        sheet = style.apply_theme(self.cfg.accent, self.cfg.theme)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(sheet)
        self.canvas.update()

    # ------------------------------------------------------- localization
    def _retranslate(self) -> None:
        self.tabs.setTabText(0, t("tab_main"))
        self.tabs.setTabText(1, t("tab_pattern"))
        self.tabs.setTabText(2, t("tab_appearance"))

        self.lbl_profiles.setText(t("weapon_profiles"))
        self.add_btn.setText(t("add"))
        self.dup_btn.setText(t("duplicate"))
        self.del_btn.setText(t("delete"))
        self.template_btn.setText(t("new_from_template"))
        self.imp_btn.setText(t("import"))
        self.exp_btn.setText(t("export"))
        self.loc_lbl.setText(t("profiles_saved_next", name=config_path().name))

        self.lbl_game.setText(t("game"))
        self.lbl_weapon_pick.setText(t("weapon_pick"))
        self.lbl_profile_settings.setText(t("profile_settings"))
        self.lbl_name.setText(t("name"))
        self.lbl_weapon.setText(t("weapon"))
        self.lbl_group.setText(t("group"))
        self.lbl_activation.setText(t("activation"))
        for i, mode in enumerate(ACTIVATION_MODES):
            self.activation.setItemText(i, t(_ACTIVATION_KEYS[mode]))
        self.template_btn.setMenu(self._build_template_menu())
        self.lbl_strength.setText(t("compensation_strength"))
        self.lbl_game_sens.setText(t("game_sensitivity"))
        self.game_sens.setToolTip(t("game_sensitivity_tip"))
        self.loop_chk.setText(t("loop_pattern"))
        self.repeat_chk.setText(t("hold_last"))

        self.lbl_random.setText(t("randomization"))
        self.random_chk.setText(t("enable_randomization"))
        self.lbl_pos_jitter.setText(t("pos_jitter"))
        self.lbl_delay_jitter.setText(t("delay_jitter"))

        self.lbl_keybinds.setText(t("keybinds"))
        self.lbl_macro_key.setText(t("macro_keybind"))
        self.lbl_switch_key.setText(t("switch_key"))
        self.switch_clear_btn.setText(t("clear_bind"))

        self.lbl_notes.setText(t("notes"))
        self.tip_lbl.setText(t("tip_canvas"))

        self.lbl_pattern.setText(t("recoil_pattern"))
        self.lbl_zoom.setText(t("zoom"))
        self.clear_btn.setText(t("clear"))
        self.lbl_steps.setText(t("steps"))
        self.add_step_btn.setText(t("add_step"))
        self.rem_step_btn.setText(t("remove_step"))
        if not self._anim_timer.isActive():
            self.anim_btn.setText(t("preview"))

        self.lbl_appearance.setText(t("appearance"))
        self.lbl_language.setText(t("language"))
        self.lbl_theme.setText(t("theme"))
        self.theme_combo.setItemText(0, t("theme_dark"))
        self.theme_combo.setItemText(1, t("theme_light"))
        self.lbl_accent.setText(t("accent_color"))
        self.accent_pick_btn.setText(t("pick_color"))
        self.lbl_global_sens.setText(t("global_sensitivity"))

        # Refresh dynamic text that embeds translated words.
        self.master_btn.setText(t("armed_on") if self.cfg.master_enabled else t("arm_off"))
        self._update_pill(False)
        self._update_switch_btn()
        self.macro_key_btn.setText(self.cfg.toggle_hotkey or t("click_to_bind"))
        self._refresh_profile_list()

    # -------------------------------------------------------- preview anim
    def _toggle_anim(self) -> None:
        if self._anim_timer.isActive():
            self._stop_anim()
            return
        profile = self._current_profile()
        if profile is None or not profile.steps:
            return
        self._anim_index = 0
        self.anim_btn.setText(t("stop"))
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
        self.anim_btn.setText(t("preview"))

    # ------------------------------------------------------------- file I/O
    def _import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("import_profile"), "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            data = json.loads(open(path, encoding="utf-8").read())
            profile = Profile.from_dict(data)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            QMessageBox.warning(self, t("import_failed"), str(exc))
            return
        self.cfg.profiles.append(profile)
        self.cfg.active_index = len(self.cfg.profiles) - 1
        self.engine.set_active_profile(self.cfg.active_profile())
        self._refresh_profile_list()
        self._load_active_into_ui()
        self._refresh_hotkeys()
        self._schedule_save()

    def _export_profile(self) -> None:
        profile = self._current_profile()
        if profile is None:
            return
        default = f"{profile.name or 'profile'}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, t("export_profile"), default, "JSON files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(profile.to_dict(), fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            QMessageBox.warning(self, t("export_failed"), str(exc))

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
    app.setStyleSheet(style.build_stylesheet())
    window = MainWindow()
    window.show()
    # Convenience: Esc disarms instantly.
    panic = QShortcut(QKeySequence(Qt.Key_Escape), window)
    panic.activated.connect(lambda: window.master_btn.setChecked(False))
    return app.exec()
