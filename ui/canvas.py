# SPDX-License-Identifier: GPL-3.0-or-later
"""Node canvas view and scene with infinite grid and wire management."""
from __future__ import annotations

import math
from typing import Dict, List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QPainter, QPen, QTransform, QWheelEvent, QMouseEvent, QKeyEvent
)
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem
)

from ..engine import NodeGraph, NodeBase, Connection, Port
from .node_item import NodeItem, PortItem
from .wire_item import WireItem, TempWireItem
from .search_dialog import NodeSearchDialog


class NodeGraphScene(QGraphicsScene):
    """The interactive node graph scene."""

    def __init__(self, graph: NodeGraph, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.setSceneRect(-5000, -5000, 10000, 10000)

        self.node_items: Dict[str, NodeItem] = {}
        self.wire_items: Dict[str, WireItem] = {}
        self.active_temp_wire: Optional[TempWireItem] = None
        self.drag_source_port: Optional[PortItem] = None

    def add_node_to_scene(self, node: NodeBase) -> NodeItem:
        self.graph.add_node(node)
        item = NodeItem(node)
        self.addItem(item)
        self.node_items[node.id] = item
        return item

    def remove_node_from_scene(self, node: NodeBase) -> None:
        if node.id in self.node_items:
            item = self.node_items.pop(node.id)
            self.removeItem(item)

        # Remove attached wires
        for conn_id, wire in list(self.wire_items.items()):
            if wire.connection.source.node == node or wire.connection.target.node == node:
                self.removeItem(wire)
                del self.wire_items[conn_id]

        self.graph.remove_node(node)

    def start_wire_drag(self, port_item: PortItem) -> None:
        self.drag_source_port = port_item
        start_pt = port_item.scenePos()
        self.active_temp_wire = TempWireItem(start_pt, is_source=not port_item.port.is_input, color_hex=port_item.port.get_color())
        self.addItem(self.active_temp_wire)

    def update_wire_drag(self, scene_pos: QPointF) -> None:
        if self.active_temp_wire:
            self.active_temp_wire.update_end(scene_pos)

    def finish_wire_drag(self, release_pos: QPointF) -> None:
        if not self.active_temp_wire or not self.drag_source_port:
            return

        self.removeItem(self.active_temp_wire)
        self.active_temp_wire = None

        # Find port under release_pos
        items = self.items(release_pos)
        target_port_item: Optional[PortItem] = None
        for it in items:
            if isinstance(it, PortItem) and it != self.drag_source_port:
                target_port_item = it
                break

        if target_port_item:
            p1 = self.drag_source_port.port
            p2 = target_port_item.port

            # Determine source (output) and target (input)
            src = p1 if not p1.is_input else (p2 if not p2.is_input else None)
            dst = p2 if p2.is_input else (p1 if p1.is_input else None)

            if src and dst:
                conn = self.graph.connect(src, dst)
                if conn:
                    src_item = self.find_port_item(src)
                    dst_item = self.find_port_item(dst)
                    wire = WireItem(conn, src_item, dst_item)
                    self.addItem(wire)
                    self.wire_items[conn.id] = wire

        self.drag_source_port = None

    def find_port_item(self, port: Port) -> Optional[PortItem]:
        node_item = self.node_items.get(port.node.id)
        if node_item:
            ports = node_item.input_ports if port.is_input else node_item.output_ports
            for pi in ports:
                if pi.port == port:
                    return pi
        return None

    def update_connected_wires(self, node_item: NodeItem) -> None:
        for wire in self.wire_items.values():
            if wire.connection.source.node == node_item.node or wire.connection.target.node == node_item.node:
                wire.update_path()

    def sync_from_graph(self) -> None:
        """Rebuild scene items from the current NodeGraph state."""
        self.clear()
        self.node_items.clear()
        self.wire_items.clear()

        for node in self.graph.nodes:
            item = NodeItem(node)
            self.addItem(item)
            self.node_items[node.id] = item

        for conn in self.graph.connections:
            src_item = self.find_port_item(conn.source)
            dst_item = self.find_port_item(conn.target)
            if src_item and dst_item:
                wire = WireItem(conn, src_item, dst_item)
                self.addItem(wire)
                self.wire_items[conn.id] = wire

    def notify_graph_changed(self) -> None:
        self.graph.notify_changed()


class NodeGraphView(QGraphicsView):
    """The interactive viewport displaying the node graph."""

    def __init__(self, scene: NodeGraphScene, parent=None):
        super().__init__(scene, parent)
        self.node_scene = scene
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.RubberBandDrag)

        self._panning = False
        self._pan_start = QPointF()

        self.setBackgroundBrush(QBrush(QColor("#181a1f")))

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, self.backgroundBrush())

        # Draw grid dots
        grid_size = 25.0
        left = math.floor(rect.left() / grid_size) * grid_size
        top = math.floor(rect.top() / grid_size) * grid_size

        dot_pen = QPen(QColor("#2c313c"), 1.5)
        painter.setPen(dot_pen)

        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(QPointF(x, y))
                y += grid_size
            x += grid_size

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Middle click or Alt+Left click initiates canvas panning
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self.node_scene.active_temp_wire:
            sp = self.mapToScene(event.pos())
            self.node_scene.update_wire_drag(sp)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        if self.node_scene.active_temp_wire:
            sp = self.mapToScene(event.pos())
            self.node_scene.finish_wire_drag(sp)

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            # Check if clicked on empty space (not a node)
            it = self.itemAt(event.pos())
            if it is None:
                self.open_search_dialog(event.pos())
                event.accept()
                return

        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Space or event.key() == Qt.Key_Tab:
            cursor_pos = self.mapFromGlobal(self.cursor().pos())
            self.open_search_dialog(cursor_pos)
            event.accept()
            return

        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            # Delete selected nodes
            for it in list(self.node_scene.selectedItems()):
                if isinstance(it, NodeItem):
                    self.node_scene.remove_node_from_scene(it.node)
            event.accept()
            return

        super().keyPressEvent(event)

    def open_search_dialog(self, view_pos) -> None:
        dlg = NodeSearchDialog(self)
        global_pt = self.mapToGlobal(view_pos)
        dlg.move(global_pt)
        if dlg.exec():
            cls = dlg.selected_node_class
            if cls:
                node = cls()
                scene_pt = self.mapToScene(view_pos)
                node.x = scene_pt.x()
                node.y = scene_pt.y()
                self.node_scene.add_node_to_scene(node)
