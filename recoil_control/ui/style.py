"""Theme stylesheet and shared colors.

Colors are module-level so the canvas can read the current palette at paint
time. Call :func:`apply_theme` to switch theme/accent at runtime, then
re-apply the returned stylesheet on the QApplication and repaint widgets.
"""

from __future__ import annotations

# Active palette (mutated by apply_theme). Defaults to the dark theme.
BG = "#0f1115"
BG_PANEL = "#171a21"
BG_ELEV = "#1e222b"
BORDER = "#2a2f3a"
TEXT = "#e6e9ef"
TEXT_DIM = "#8b93a7"
ACCENT = "#27d796"
ACCENT_DIM = "#1f9e72"
ON_ACCENT = "#06281d"
DANGER = "#ff5c5c"
WARN = "#ffb454"

GRID = "#222734"
GRID_AXIS = "#384055"
PATH = ACCENT
POINT = "#5cc8ff"
POINT_SEL = "#ffb454"
MARKER = "#ff5c5c"

_THEMES = {
    "dark": {
        "BG": "#0f1115",
        "BG_PANEL": "#171a21",
        "BG_ELEV": "#1e222b",
        "BORDER": "#2a2f3a",
        "TEXT": "#e6e9ef",
        "TEXT_DIM": "#8b93a7",
        "GRID": "#222734",
        "GRID_AXIS": "#384055",
        "POINT": "#5cc8ff",
        "POINT_SEL": "#ffb454",
        "MARKER": "#ff5c5c",
    },
    "light": {
        "BG": "#f3f5f9",
        "BG_PANEL": "#ffffff",
        "BG_ELEV": "#e9edf4",
        "BORDER": "#cdd4e0",
        "TEXT": "#1b2030",
        "TEXT_DIM": "#5d6680",
        "GRID": "#dfe4ee",
        "GRID_AXIS": "#b4bdd0",
        "POINT": "#2a7fd0",
        "POINT_SEL": "#d98a17",
        "MARKER": "#e23b3b",
    },
}


def _darken(hex_color: str, factor: float = 0.78) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, min(255, int(c * factor))) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _readable_on(hex_color: str) -> str:
    """Black or near-black/white text that reads on the accent color."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "#06281d"
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#0c0f14" if luminance > 0.6 else "#ffffff"


def apply_theme(accent: str, theme: str = "dark") -> str:
    """Update the active palette and return the matching stylesheet."""
    global BG, BG_PANEL, BG_ELEV, BORDER, TEXT, TEXT_DIM
    global ACCENT, ACCENT_DIM, ON_ACCENT, PATH
    global GRID, GRID_AXIS, POINT, POINT_SEL, MARKER

    pal = _THEMES.get(theme, _THEMES["dark"])
    BG = pal["BG"]
    BG_PANEL = pal["BG_PANEL"]
    BG_ELEV = pal["BG_ELEV"]
    BORDER = pal["BORDER"]
    TEXT = pal["TEXT"]
    TEXT_DIM = pal["TEXT_DIM"]
    GRID = pal["GRID"]
    GRID_AXIS = pal["GRID_AXIS"]
    POINT = pal["POINT"]
    POINT_SEL = pal["POINT_SEL"]
    MARKER = pal["MARKER"]

    ACCENT = accent or "#27d796"
    ACCENT_DIM = _darken(ACCENT)
    ON_ACCENT = _readable_on(ACCENT)
    PATH = ACCENT
    return build_stylesheet()


def build_stylesheet() -> str:
    return f"""
* {{
    font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#root {{
    background: {BG};
}}
QWidget#header {{
    background: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}
QLabel#title {{
    font-size: 16px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#subtitle {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QFrame#panel, QWidget#panel {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QLabel.sectionTitle, QLabel#sectionTitle {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    top: -1px;
}}
QTabBar::tab {{
    background: {BG_ELEV};
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    padding: 7px 16px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {BG_PANEL};
    color: {TEXT};
    border-bottom-color: {BG_PANEL};
}}
QPushButton {{
    background: {BG_ELEV};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 12px;
    color: {TEXT};
}}
QPushButton:hover {{ border-color: {ACCENT_DIM}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; border-color: {BORDER}; }}
QPushButton::menu-indicator {{ subcontrol-position: right center; right: 6px; }}
QPushButton#primary {{
    background: {ACCENT_DIM};
    border: 1px solid {ACCENT};
    color: {ON_ACCENT};
    font-weight: 700;
}}
QPushButton#primary:hover {{ background: {ACCENT}; }}
QPushButton#danger:hover {{ border-color: {DANGER}; color: {DANGER}; }}

QPushButton#master {{
    font-size: 15px;
    font-weight: 800;
    padding: 10px 18px;
    border-radius: 10px;
    background: {BG_ELEV};
    border: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QPushButton#master:checked {{
    background: {ACCENT_DIM};
    border: 1px solid {ACCENT};
    color: {ON_ACCENT};
}}

QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QPlainTextEdit {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {ACCENT_DIM};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {BG_ELEV};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DIM};
}}
QMenu {{
    background: {BG_ELEV};
    border: 1px solid {BORDER};
    padding: 4px;
}}
QMenu::item {{ padding: 6px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACCENT_DIM}; color: {ON_ACCENT}; }}

QListWidget {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 8px 10px;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background: {ACCENT_DIM};
    color: {ON_ACCENT};
}}
QListWidget::item:hover:!selected {{ background: {BG_ELEV}; }}

QTableWidget {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
}}
QHeaderView::section {{
    background: {BG_ELEV};
    color: {TEXT_DIM};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 6px;
    font-weight: 700;
}}
QTableWidget::item:selected {{ background: {ACCENT_DIM}; color: {ON_ACCENT}; }}

QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {BORDER};
    border-radius: 5px;
    background: {BG};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

QLabel#statusPill {{
    border-radius: 11px;
    padding: 4px 12px;
    font-weight: 800;
    font-size: 11px;
    background: {BG_ELEV};
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
}}
QLabel#statusPillOn {{
    border-radius: 11px;
    padding: 4px 12px;
    font-weight: 800;
    font-size: 11px;
    background: {ACCENT_DIM};
    color: {ON_ACCENT};
    border: 1px solid {ACCENT};
}}
QSplitter::handle {{ background: {BORDER}; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {BG_ELEV}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""


# Backwards-compatible default stylesheet.
STYLESHEET = build_stylesheet()
