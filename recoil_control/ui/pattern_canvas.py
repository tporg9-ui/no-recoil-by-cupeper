"""Interactive recoil-pattern canvas.

Visualizes the cumulative mouse path produced by a profile's steps and
lets the user add points (click), move points (drag) and delete points
(right-click). The canvas mutates the live Step objects of the profile
and emits ``changed`` so the rest of the UI can refresh and autosave.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget

from ..model import Profile, Step
from . import style


class PatternCanvas(QWidget):
    changed = Signal()
    pointSelected = Signal(int)  # -1 when nothing selected

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 320)
        self.setMouseTracking(True)
        self._profile: Optional[Profile] = None
        self._scale = 6.0  # pixels per mouse count
        self._selected = -1
        self._dragging = False
        self._marker = -1  # animation/preview marker step index
        self._default_delay = 30
        self._hit_radius = 11

    # -- public API -------------------------------------------------------
    def set_profile(self, profile: Optional[Profile]) -> None:
        self._profile = profile
        self._selected = -1
        self._marker = -1
        self.pointSelected.emit(-1)
        self.update()

    def set_scale(self, scale: float) -> None:
        self._scale = max(1.0, float(scale))
        self.update()

    def set_default_delay(self, delay_ms: int) -> None:
        self._default_delay = max(1, int(delay_ms))

    def set_marker(self, index: int) -> None:
        self._marker = index
        self.update()

    def selected_index(self) -> int:
        return self._selected

    def select(self, index: int) -> None:
        self._selected = index
        self.update()

    def clear_points(self) -> None:
        if self._profile is None:
            return
        self._profile.steps.clear()
        self._selected = -1
        self.pointSelected.emit(-1)
        self.changed.emit()
        self.update()

    # -- geometry helpers -------------------------------------------------
    def _origin(self) -> QPointF:
        # Start point near top-center; pattern grows downward.
        return QPointF(self.width() / 2.0, self.height() * 0.18)

    def _cumulative(self) -> list[QPointF]:
        """Screen positions for the start point + each step."""
        pts = [self._origin()]
        if self._profile is None:
            return pts
        cx = 0.0
        cy = 0.0
        o = self._origin()
        for s in self._profile.steps:
            cx += s.dx
            cy += s.dy
            pts.append(QPointF(o.x() + cx * self._scale, o.y() + cy * self._scale))
        return pts

    def _screen_to_counts(self, p: QPointF) -> QPointF:
        o = self._origin()
        return QPointF((p.x() - o.x()) / self._scale, (p.y() - o.y()) / self._scale)

    # -- mouse interaction ------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if self._profile is None:
            return
        pos = event.position()
        pts = self._cumulative()

        if event.button() == Qt.RightButton:
            hit = self._hit_test(pos, pts)
            if hit >= 1:  # never delete the start anchor (index 0)
                del self._profile.steps[hit - 1]
                self._selected = -1
                self.pointSelected.emit(-1)
                self.changed.emit()
                self.update()
            return

        if event.button() == Qt.LeftButton:
            hit = self._hit_test(pos, pts)
            if hit >= 1:
                self._selected = hit - 1
                self._dragging = True
                self.pointSelected.emit(self._selected)
                self.update()
            elif hit == 0:
                self._selected = -1
                self.pointSelected.emit(-1)
                self.update()
            else:
                # Add a new point as a delta from the last cumulative pos.
                last = pts[-1]
                c_last = self._screen_to_counts(last)
                c_new = self._screen_to_counts(pos)
                step = Step(
                    round(c_new.x() - c_last.x(), 2),
                    round(c_new.y() - c_last.y(), 2),
                    self._default_delay,
                )
                self._profile.steps.append(step)
                self._selected = len(self._profile.steps) - 1
                self.pointSelected.emit(self._selected)
                self.changed.emit()
                self.update()

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging or self._profile is None or self._selected < 0:
            return
        pts = self._cumulative()
        prev = pts[self._selected]  # cumulative position before selected step
        c_prev = self._screen_to_counts(prev)
        c_new = self._screen_to_counts(event.position())
        step = self._profile.steps[self._selected]
        step.dx = round(c_new.x() - c_prev.x(), 2)
        step.dy = round(c_new.y() - c_prev.y(), 2)
        self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False

    def _hit_test(self, pos: QPointF, pts: list[QPointF]) -> int:
        for i, p in enumerate(pts):
            if (p - pos).manhattanLength() <= self._hit_radius * 1.6:
                if (p.x() - pos.x()) ** 2 + (p.y() - pos.y()) ** 2 <= self._hit_radius ** 2:
                    return i
        return -1

    # -- painting ---------------------------------------------------------
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(style.BG))
        self._draw_grid(painter)

        pts = self._cumulative()

        # Path
        if len(pts) >= 2:
            pen = QPen(QColor(style.PATH), 2)
            painter.setPen(pen)
            for a, b in zip(pts, pts[1:]):
                painter.drawLine(a, b)

        # Start anchor
        self._draw_point(painter, pts[0], QColor(style.GRID_AXIS), "S", small=True)

        # Step points
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        for idx in range(1, len(pts)):
            step_i = idx - 1
            if step_i == self._marker:
                color = QColor(style.MARKER)
            elif step_i == self._selected:
                color = QColor(style.POINT_SEL)
            else:
                color = QColor(style.POINT)
            self._draw_point(painter, pts[idx], color, str(idx))

        # Empty hint
        if self._profile is None or not self._profile.steps:
            painter.setPen(QColor(style.TEXT_DIM))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Click to add recoil points\n(drag to move, right-click to delete)",
            )

    def _draw_grid(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        o = self._origin()
        step = max(12.0, self._scale * 5)
        pen = QPen(QColor(style.GRID), 1)
        painter.setPen(pen)
        x = o.x()
        while x < w:
            painter.drawLine(QPointF(x, 0), QPointF(x, h))
            x += step
        x = o.x() - step
        while x > 0:
            painter.drawLine(QPointF(x, 0), QPointF(x, h))
            x -= step
        y = o.y()
        while y < h:
            painter.drawLine(QPointF(0, y), QPointF(w, y))
            y += step
        y = o.y() - step
        while y > 0:
            painter.drawLine(QPointF(0, y), QPointF(w, y))
            y -= step
        # Axes through the origin
        axis = QPen(QColor(style.GRID_AXIS), 1)
        painter.setPen(axis)
        painter.drawLine(QPointF(o.x(), 0), QPointF(o.x(), h))
        painter.drawLine(QPointF(0, o.y()), QPointF(w, o.y()))

    def _draw_point(self, painter: QPainter, p: QPointF, color: QColor, label: str, small: bool = False) -> None:
        r = 6 if small else 9
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(style.BG), 2))
        painter.drawEllipse(p, r, r)
        if not small:
            painter.setPen(QColor(style.BG))
            painter.drawText(
                p.x() - r, p.y() - r, 2 * r, 2 * r, Qt.AlignCenter, label
            )
