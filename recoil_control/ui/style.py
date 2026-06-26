"""Dark theme stylesheet and shared colors."""

# Palette
BG = "#0f1115"
BG_PANEL = "#171a21"
BG_ELEV = "#1e222b"
BORDER = "#2a2f3a"
TEXT = "#e6e9ef"
TEXT_DIM = "#8b93a7"
ACCENT = "#27d796"
ACCENT_DIM = "#1f9e72"
DANGER = "#ff5c5c"
WARN = "#ffb454"

GRID = "#222734"
GRID_AXIS = "#384055"
PATH = "#27d796"
POINT = "#5cc8ff"
POINT_SEL = "#ffb454"
MARKER = "#ff5c5c"


STYLESHEET = f"""
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
QPushButton#primary {{
    background: {ACCENT_DIM};
    border: 1px solid {ACCENT};
    color: #06281d;
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
    color: #06281d;
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
    color: #06281d;
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
QTableWidget::item:selected {{ background: {ACCENT_DIM}; color: #06281d; }}

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
    color: #06281d;
    border: 1px solid {ACCENT};
}}
QSplitter::handle {{ background: {BORDER}; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {BG_ELEV}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
