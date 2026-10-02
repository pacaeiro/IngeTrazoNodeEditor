# SPDX-License-Identifier: GPL-3.0-or-later
"""Wire graphics items rendering smooth cubic Bezier connections."""
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath, QPen, QColor, QPainter
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItem


class WireItem(QGraphicsPathItem):
    """A Bezier wire connecting an output port to an input port."""

    def __init__(self, connection, source_item, target_item):
        super().__init__()
        self.connection = connection
        self.source_item = source_item
        self.target_item = target_item
        self.setZValue(-1)  # Wires sit behind node cards
        self.setAcceptHoverEvents(True)

        color_hex = self.connection.source.get_color()
        self.base_color = QColor(color_hex)
        self.pen = QPen(self.base_color, 2.5, Qt.SolidLine, Qt.RoundCap)
        self.setPen(self.pen)
        self.update_path()

    def update_path(self) -> None:
        if not self.source_item or not self.target_item:
            return

        p1 = self.source_item.scenePos()
        p2 = self.target_item.scenePos()

        path = QPainterPath()
        path.moveTo(p1)

        dx = abs(p2.x() - p1.x()) * 0.5
        dx = max(30.0, dx)

        ctrl1 = QPointF(p1.x() + dx, p1.y())
        ctrl2 = QPointF(p2.x() - dx, p2.y())

        path.cubicTo(ctrl1, ctrl2, p2)
        self.setPath(path)

    def hoverEnterEvent(self, event) -> None:
        self.setPen(QPen(QColor("#ffffff"), 3.5, Qt.SolidLine, Qt.RoundCap))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.setPen(self.pen)
        super().hoverLeaveEvent(event)


class TempWireItem(QGraphicsPathItem):
    """Interactive wire during mouse dragging from a port."""

    def __init__(self, start_pos: QPointF, is_source: bool = True, color_hex: str = "#4fc1ff"):
        super().__init__()
        self.start_pos = start_pos
        self.is_source = is_source
        self.setZValue(100)
        self.color = QColor(color_hex)
        self.pen = QPen(self.color, 2.5, Qt.DashLine, Qt.RoundCap)
        self.setPen(self.pen)

    def update_end(self, end_pos: QPointF) -> None:
        path = QPainterPath()
        p1 = self.start_pos if self.is_source else end_pos
        p2 = end_pos if self.is_source else self.start_pos

        path.moveTo(p1)
        dx = abs(p2.x() - p1.x()) * 0.5
        dx = max(30.0, dx)

        ctrl1 = QPointF(p1.x() + dx, p1.y())
        ctrl2 = QPointF(p2.x() - dx, p2.y())
        path.cubicTo(ctrl1, ctrl2, p2)
        self.setPath(path)
