# SPDX-License-Identifier: GPL-3.0-or-later
"""Node graphics item and port sockets with embedded interactive widgets."""
from __future__ import annotations

from typing import List, Optional, Any
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
)
from PySide6.QtWidgets import (
    QGraphicsItem, QGraphicsObject, QGraphicsProxyWidget,
    QSlider, QDoubleSpinBox, QCheckBox, QLineEdit, QPlainTextEdit, QWidget, QHBoxLayout, QVBoxLayout, QLabel
)

from ..engine import NodeBase, Port, PortType


class PortItem(QGraphicsItem):
    """Circular socket for a single Port."""

    RADIUS = 6.0

    def __init__(self, port: Port, parent: NodeItem):
        super().__init__(parent)
        self.port = port
        self.node_item = parent
        self.setAcceptHoverEvents(True)
        self.is_hovered = False
        color_hex = port.get_color()
        self.brush = QBrush(QColor(color_hex))
        self.pen = QPen(QColor("#1e1e1e"), 1.5)

    def boundingRect(self) -> QRectF:
        r = self.RADIUS + 3.0
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        if self.is_hovered:
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.setPen(QPen(QColor(self.port.get_color()), 2.0))
        else:
            painter.setBrush(self.brush)
            painter.setPen(self.pen)

        painter.drawEllipse(QPointF(0, 0), self.RADIUS, self.RADIUS)

    def hoverEnterEvent(self, event) -> None:
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.scene().start_wire_drag(self)
            event.accept()
        else:
            super().mousePressEvent(event)


class NodeItem(QGraphicsObject):
    """Visual card for a NodeBase."""

    HEADER_HEIGHT = 28.0
    CORNER_RADIUS = 7.0
    ROW_HEIGHT = 22.0
    MIN_WIDTH = 150.0

    def __init__(self, node: NodeBase):
        super().__init__()
        self.node = node
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.input_ports: List[PortItem] = []
        self.output_ports: List[PortItem] = []
        self.widget_proxy: Optional[QGraphicsProxyWidget] = None
        self.width = self.MIN_WIDTH
        self.height = 80.0

        self.setPos(node.x, node.y)
        self.build_ui()

    def build_ui(self) -> None:
        # Determine height based on port count and widgets
        port_rows = max(len(self.node.inputs), len(self.node.outputs))
        content_height = max(30.0, port_rows * self.ROW_HEIGHT)

        # Check if node has embedded widget
        has_widget = self.has_custom_widget()
        if has_widget:
            t_name = self.node.__class__.__name__
            if t_name == "PanelNode":
                content_height += 124.0
                self.width = max(self.width, 220.0)
            else:
                content_height += 44.0
                self.width = max(self.width, 220.0 if t_name == "ExpressionNode" else 210.0)

        self.height = self.HEADER_HEIGHT + content_height + 10.0

        # Create input port items (left side)
        y_cursor = self.HEADER_HEIGHT + 14.0
        for port in self.node.inputs:
            pi = PortItem(port, self)
            pi.setPos(0, y_cursor)
            self.input_ports.append(pi)
            y_cursor += self.ROW_HEIGHT

        # Create output port items (right side)
        y_cursor = self.HEADER_HEIGHT + 14.0
        for port in self.node.outputs:
            pi = PortItem(port, self)
            pi.setPos(self.width, y_cursor)
            self.output_ports.append(pi)
            y_cursor += self.ROW_HEIGHT

        # Add embedded interactive widget if applicable
        if has_widget:
            self.add_embedded_widget()

    def has_custom_widget(self) -> bool:
        t = self.node.__class__.__name__
        return t in ("NumberSliderNode", "IntegerSliderNode", "ToggleNode", "StringNode", "ExpressionNode", "PanelNode")

    def add_embedded_widget(self) -> None:
        t = self.node.__class__.__name__
        proxy = QGraphicsProxyWidget(self)

        container = QWidget()
        container.setStyleSheet("background: transparent;")

        if t in ("NumberSliderNode", "IntegerSliderNode"):
            is_int = (t == "IntegerSliderNode")
            min_val = float(self.node.widget_values.get("min", 0.0))
            max_val = float(self.node.widget_values.get("max", 50.0 if not is_int else 100.0))
            cur_val = float(self.node.widget_values.get("value", 5.0 if not is_int else 10))

            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 2, 10, 2)
            layout.setSpacing(6)

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            steps = int(round(max_val - min_val)) if is_int else 1000
            slider.setMaximum(max(1, steps))

            if is_int:
                initial_tick = int(round(cur_val - min_val))
            else:
                ratio = (cur_val - min_val) / (max_val - min_val) if max_val > min_val else 0.0
                initial_tick = int(round(ratio * 1000))
            slider.setValue(max(0, min(steps, initial_tick)))

            spin = QDoubleSpinBox()
            spin.setDecimals(0 if is_int else 2)
            spin.setRange(min_val, max_val)
            spin.setSingleStep(1.0 if is_int else 0.1)
            spin.setValue(cur_val)
            spin.setFixedWidth(56)

            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 5px;
                    background: #282c34;
                    border-radius: 2px;
                }
                QSlider::sub-page:horizontal {
                    background: #4fc1ff;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #eceff4;
                    border: 1px solid #3b4252;
                    width: 14px;
                    height: 14px;
                    margin: -5px 0;
                    border-radius: 7px;
                }
                QSlider::handle:horizontal:hover {
                    background: #ffffff;
                    border: 1px solid #4fc1ff;
                }
            """)

            spin.setStyleSheet("""
                QDoubleSpinBox {
                    background: #252830;
                    color: #eceff4;
                    border: 1px solid #434c5e;
                    border-radius: 4px;
                    padding: 2px 2px 2px 4px;
                    font-size: 11px;
                }
                QDoubleSpinBox::up-button {
                    subcontrol-origin: border;
                    subcontrol-position: top right;
                    width: 15px;
                    background: #2e3440;
                    border-left: 1px solid #434c5e;
                    border-bottom: 1px solid #3b4252;
                }
                QDoubleSpinBox::down-button {
                    subcontrol-origin: border;
                    subcontrol-position: bottom right;
                    width: 15px;
                    background: #2e3440;
                    border-left: 1px solid #434c5e;
                }
                QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                    background: #4c566a;
                }
                QDoubleSpinBox::up-arrow {
                    width: 0;
                    height: 0;
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-bottom: 4px solid #ffffff;
                }
                QDoubleSpinBox::down-arrow {
                    width: 0;
                    height: 0;
                    border-left: 3px solid transparent;
                    border-right: 3px solid transparent;
                    border-top: 4px solid #ffffff;
                }
            """)

            syncing = [False]

            def on_slider_moved(val):
                if syncing[0]:
                    return
                syncing[0] = True
                if is_int:
                    num = int(min_val + val)
                else:
                    ratio = val / 1000.0
                    num = min_val + ratio * (max_val - min_val)
                spin.setValue(num)
                self.node.widget_values["value"] = num
                self.node.dirty = True
                if self.scene():
                    self.scene().notify_graph_changed()
                syncing[0] = False

            def on_spin_changed(num):
                if syncing[0]:
                    return
                syncing[0] = True
                if is_int:
                    tick = int(round(num - min_val))
                else:
                    ratio = (num - min_val) / (max_val - min_val) if max_val > min_val else 0.0
                    tick = int(round(ratio * 1000))
                slider.setValue(max(0, min(steps, tick)))
                self.node.widget_values["value"] = int(num) if is_int else float(num)
                self.node.dirty = True
                if self.scene():
                    self.scene().notify_graph_changed()
                syncing[0] = False

            slider.valueChanged.connect(on_slider_moved)
            spin.valueChanged.connect(on_spin_changed)

            layout.addWidget(slider, 1)
            layout.addWidget(spin, 0)

        elif t == "ToggleNode":
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setSpacing(6)
            cb = QCheckBox("Active")
            cb.setChecked(bool(self.node.widget_values.get("value", True)))
            cb.setStyleSheet("color: #eceff4; font-size: 11px;")

            def on_toggle(checked):
                self.node.widget_values["value"] = checked
                self.node.dirty = True
                if self.scene():
                    self.scene().notify_graph_changed()

            cb.toggled.connect(on_toggle)
            layout.addWidget(cb)

        elif t == "StringNode":
            layout = QHBoxLayout(container)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setSpacing(6)
            le = QLineEdit(str(self.node.widget_values.get("value", "")))
            le.setStyleSheet("""
                QLineEdit {
                    background: #252830;
                    color: #eceff4;
                    border: 1px solid #434c5e;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
            """)

            def on_text(txt):
                self.node.widget_values["value"] = txt
                self.node.dirty = True
                if self.scene():
                    self.scene().notify_graph_changed()

            le.textChanged.connect(on_text)
            layout.addWidget(le)

        elif t == "ExpressionNode":
            layout = QHBoxLayout(container)
            layout.setContentsMargins(8, 0, 8, 0)
            layout.setSpacing(4)
            cur_expr = str(self.node.widget_values.get("expr", "x + y"))
            le = QLineEdit(cur_expr)
            le.setPlaceholderText("e.g. sin(x)*cos(y)")
            le.setStyleSheet("""
                QLineEdit {
                    background: #181a20;
                    color: #56b6c2;
                    border: 1px solid #434c5e;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 11px;
                    font-weight: bold;
                }
                QLineEdit:focus {
                    border: 1px solid #88c0d0;
                    background: #1e222b;
                }
            """)

            def on_expr_changed(txt):
                self.node.widget_values["expr"] = txt
                self.node.dirty = True
                if self.scene():
                    self.scene().notify_graph_changed()

            le.textChanged.connect(on_expr_changed)
            layout.addWidget(le)

        elif t == "PanelNode":
            layout = QVBoxLayout(container)
            layout.setContentsMargins(6, 0, 6, 4)
            layout.setSpacing(0)

            pte = QPlainTextEdit()
            pte.setPlaceholderText("// Double-click or type data...\n// or connect wire to view data")
            pte.setStyleSheet("""
                QPlainTextEdit {
                    background: #181a20;
                    color: #d8dee9;
                    border: 1px solid #3b4252;
                    border-radius: 4px;
                    padding: 4px 6px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 11px;
                    selection-background-color: #3b4252;
                    selection-color: #88c0d0;
                }
                QPlainTextEdit:focus {
                    border: 1px solid #88c0d0;
                }
                QScrollBar:vertical {
                    background: #181a20;
                    width: 10px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    background: #3b4252;
                    min-height: 20px;
                    border-radius: 3px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #4c566a;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)

            # Load initial content
            init_val = self.node.widget_values.get("display") or self.node.widget_values.get("text") or ""
            pte.setPlainText(str(init_val))

            is_connected = self.node.inputs[0].has_connection if self.node.inputs else False
            pte.setReadOnly(is_connected)

            syncing = [False]

            def on_panel_text():
                if syncing[0]:
                    return
                if self.node.inputs and self.node.inputs[0].has_connection:
                    return
                syncing[0] = True
                txt = pte.toPlainText()
                self.node.widget_values["text"] = txt
                self.node.widget_values["display"] = txt
                self.node.dirty = True
                if self.scene():
                    self.scene().notify_graph_changed()
                syncing[0] = False

            def update_panel_ui(text_val: str):
                if syncing[0]:
                    return
                syncing[0] = True
                conn = self.node.inputs[0].has_connection if self.node.inputs else False
                pte.setReadOnly(conn)
                if pte.toPlainText() != text_val:
                    sb = pte.verticalScrollBar()
                    pos = sb.value() if sb else 0
                    pte.setPlainText(text_val)
                    if sb:
                        sb.setValue(pos)
                syncing[0] = False

            self.node.on_display_updated = update_panel_ui
            pte.textChanged.connect(on_panel_text)
            layout.addWidget(pte)

        self.widget_proxy = proxy
        proxy.setWidget(container)
        if t == "PanelNode":
            widget_y = self.HEADER_HEIGHT + self.ROW_HEIGHT + 6.0
            widget_h = self.height - widget_y - 8.0
            proxy.setPos(0, widget_y)
            proxy.resize(self.width, max(40.0, widget_h))
        else:
            widget_y = self.height - 38.0
            proxy.setPos(0, widget_y)
            proxy.resize(self.width, 32.0)

    def rebuild_ports(self) -> None:
        """Dynamically rebuild port items when dynamic ports change (e.g. ExpressionNode)."""
        # Unparent and remove old port items
        for pi in self.input_ports:
            pi.setParentItem(None)
            if self.scene():
                self.scene().removeItem(pi)
        for pi in self.output_ports:
            pi.setParentItem(None)
            if self.scene():
                self.scene().removeItem(pi)
        self.input_ports.clear()
        self.output_ports.clear()

        # Recalculate dimensions
        port_rows = max(len(self.node.inputs), len(self.node.outputs))
        content_height = max(30.0, port_rows * self.ROW_HEIGHT)
        has_widget = self.has_custom_widget()
        if has_widget:
            t_name = self.node.__class__.__name__
            if t_name == "PanelNode":
                content_height += 124.0
                self.width = max(self.width, 220.0)
            else:
                content_height += 44.0
                self.width = max(self.width, 220.0 if t_name == "ExpressionNode" else 210.0)

        self.prepareGeometryChange()
        self.height = self.HEADER_HEIGHT + content_height + 10.0

        # Re-create input port items (left side)
        y_cursor = self.HEADER_HEIGHT + 14.0
        for port in self.node.inputs:
            pi = PortItem(port, self)
            pi.setPos(0, y_cursor)
            self.input_ports.append(pi)
            y_cursor += self.ROW_HEIGHT

        # Re-create output port items (right side)
        y_cursor = self.HEADER_HEIGHT + 14.0
        for port in self.node.outputs:
            pi = PortItem(port, self)
            pi.setPos(self.width, y_cursor)
            self.output_ports.append(pi)
            y_cursor += self.ROW_HEIGHT

        # Reposition embedded widget if present
        proxy = self.widget_proxy
        if proxy is None:
            for child in self.childItems():
                if isinstance(child, QGraphicsProxyWidget):
                    proxy = child
                    break

        if proxy is not None:
            t_name = self.node.__class__.__name__
            if t_name == "PanelNode":
                widget_y = self.HEADER_HEIGHT + self.ROW_HEIGHT + 6.0
                widget_h = self.height - widget_y - 8.0
                proxy.setPos(0, widget_y)
                proxy.resize(self.width, max(40.0, widget_h))
            else:
                widget_y = self.height - 38.0
                proxy.setPos(0, widget_y)
                proxy.resize(self.width, 32.0)

        # Update paths of connected wires
        if self.scene() and hasattr(self.scene(), "wire_items"):
            for wire in self.scene().wire_items.values():
                if wire.connection.source.node == self.node:
                    wire.source_item = self.scene().find_port_item(wire.connection.source)
                    wire.update_path()
                elif wire.connection.target.node == self.node:
                    wire.target_item = self.scene().find_port_item(wire.connection.target)
                    wire.update_path()

        self.update()


    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)

        # Background card
        rect = self.boundingRect()
        bg_path = QPainterPath()
        bg_path.addRoundedRect(rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        # Card shadow & fill
        card_color = QColor("#1e222b")
        if self.isSelected():
            painter.setPen(QPen(QColor("#88c0d0"), 2.0))
        elif self.node.error:
            painter.setPen(QPen(QColor("#bf616a"), 2.0))
            err_tip = f"❌ {self.node.error}"
            if self.toolTip() != err_tip:
                self.setToolTip(err_tip)
        else:
            painter.setPen(QPen(QColor("#333842"), 1.2))
            desc_tip = self.node.description or self.node.name
            if self.toolTip() != desc_tip:
                self.setToolTip(desc_tip)

        painter.setBrush(QBrush(card_color))
        painter.drawPath(bg_path)

        # Header bar
        header_rect = QRectF(0, 0, self.width, self.HEADER_HEIGHT)
        header_path = QPainterPath()
        header_path.addRoundedRect(rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        header_clip = QPainterPath()
        header_clip.addRect(header_rect)
        final_header = header_path.intersected(header_clip)

        header_brush = QBrush(QColor(self.node.header_color))
        painter.setPen(Qt.NoPen)
        painter.setBrush(header_brush)
        painter.drawPath(final_header)

        # Header Title
        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(10, 0, self.width - 20, self.HEADER_HEIGHT), Qt.AlignVCenter | Qt.AlignLeft, self.node.name)

        # Port Labels
        port_font = QFont("Segoe UI", 8)
        painter.setFont(port_font)
        painter.setPen(QPen(QColor("#abb2bf")))

        # Input labels (left)
        y_cur = self.HEADER_HEIGHT + 7.0
        for port in self.node.inputs:
            painter.drawText(QRectF(12, y_cur, self.width * 0.5, self.ROW_HEIGHT), Qt.AlignVCenter | Qt.AlignLeft, port.name)
            y_cur += self.ROW_HEIGHT

        # Output labels (right)
        y_cur = self.HEADER_HEIGHT + 7.0
        for port in self.node.outputs:
            painter.drawText(QRectF(self.width * 0.5 - 12, y_cur, self.width * 0.5, self.ROW_HEIGHT), Qt.AlignVCenter | Qt.AlignRight, port.name)
            y_cur += self.ROW_HEIGHT

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            self.node.x = new_pos.x()
            self.node.y = new_pos.y()
            if hasattr(self.scene(), "update_connected_wires"):
                self.scene().update_connected_wires(self)
        return super().itemChange(change, value)
