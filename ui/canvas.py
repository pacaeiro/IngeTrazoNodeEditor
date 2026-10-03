# SPDX-License-Identifier: GPL-3.0-or-later
"""Node canvas view and scene with infinite grid, wire management, wire cutting, and copy/paste."""
from __future__ import annotations

import math
import copy
from typing import Dict, List, Optional, Set, Any
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QPainter, QPen, QTransform, QWheelEvent, QMouseEvent, QKeyEvent,
    QPainterPath, QPainterPathStroker
)
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsProxyWidget,
    QGraphicsPathItem, QApplication, QWidget
)

from ..engine import NodeGraph, NodeBase, Connection, Port, PortType
from .node_item import NodeItem, PortItem
from .wire_item import WireItem, TempWireItem
from .search_dialog import NodeSearchDialog
from ..nodes_library import NODE_REGISTRY


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

        # Remove attached wires and record other nodes affected
        affected_nodes: Set[NodeBase] = set()
        for conn_id, wire in list(self.wire_items.items()):
            if wire.connection.source.node == node or wire.connection.target.node == node:
                other = wire.connection.target.node if wire.connection.source.node == node else wire.connection.source.node
                affected_nodes.add(other)
                self.removeItem(wire)
                del self.wire_items[conn_id]

        self.graph.remove_node(node)

        # Check affected nodes for dynamic ports (e.g. ExpressionNode)
        for other in affected_nodes:
            if hasattr(other, "sync_dynamic_ports"):
                if other.sync_dynamic_ports():
                    node_item = self.node_items.get(other.id)
                    if node_item:
                        node_item.rebuild_ports()

    def start_wire_drag(self, port_item: PortItem) -> None:
        self.drag_source_port = port_item
        start_pt = port_item.scenePos()
        self.active_temp_wire = TempWireItem(start_pt, is_source=not port_item.port.is_input, color_hex=port_item.port.get_color())
        self.addItem(self.active_temp_wire)

    def update_wire_drag(self, scene_pos: QPointF) -> None:
        if self.active_temp_wire:
            self.active_temp_wire.update_end(scene_pos)

    def finish_wire_drag(self, release_pos: QPointF, is_shift: bool = False) -> None:
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
                # If not holding shift, disconnect and visually remove existing wires to dst
                if not is_shift:
                    for wire in list(self.wire_items.values()):
                        if wire.connection.target == dst:
                            self.removeItem(wire)
                            if wire.connection.id in self.wire_items:
                                del self.wire_items[wire.connection.id]

                conn = self.graph.connect(src, dst, append=is_shift)
                if conn:
                    if conn.id not in self.wire_items:
                        src_item = self.find_port_item(src)
                        dst_item = self.find_port_item(dst)
                        if src_item and dst_item:
                            wire = WireItem(conn, src_item, dst_item)
                            self.addItem(wire)
                            self.wire_items[conn.id] = wire

                # If target node has dynamic ports (e.g. ExpressionNode), sync them
                if hasattr(dst.node, "sync_dynamic_ports"):
                    if dst.node.sync_dynamic_ports():
                        node_item = self.node_items.get(dst.node.id)
                        if node_item:
                            node_item.rebuild_ports()

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

        # Wire cutting (laser slice) state
        self._cutting = False
        self._cut_path = QPainterPath()
        self._cut_points: List[QPointF] = []
        self._cut_line_item: Optional[QGraphicsPathItem] = None

        # Clipboard for Copy & Paste
        self._clipboard: Optional[dict] = None
        self._paste_offset = 35.0

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
        # Ctrl + Left click initiates wire cutting (laser slice)
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            self._cutting = True
            sp = self.mapToScene(event.pos())
            self._cut_path = QPainterPath()
            self._cut_path.moveTo(sp)
            self._cut_points = [sp]

            self._cut_line_item = QGraphicsPathItem()
            self._cut_line_item.setZValue(500)
            cut_pen = QPen(QColor("#ff3344"), 2.5, Qt.DashLine, Qt.RoundCap)
            self._cut_line_item.setPen(cut_pen)
            self.node_scene.addItem(self._cut_line_item)
            self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        # Middle click or Alt+Left click initiates canvas panning
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if getattr(self, "_cutting", False):
            sp = self.mapToScene(event.pos())
            self._cut_points.append(sp)
            self._cut_path.lineTo(sp)
            if self._cut_line_item:
                self._cut_line_item.setPath(self._cut_path)
            event.accept()
            return

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
        if getattr(self, "_cutting", False) and event.button() == Qt.LeftButton:
            self._cutting = False
            self.setCursor(Qt.ArrowCursor)

            if self._cut_line_item:
                if self._cut_line_item in self.node_scene.items():
                    self.node_scene.removeItem(self._cut_line_item)
                self._cut_line_item = None

            if len(self._cut_points) >= 2:
                self.slice_wires(self._cut_path)

            event.accept()
            return

        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return

        if self.node_scene.active_temp_wire:
            sp = self.mapToScene(event.pos())
            is_shift = bool(
                (event.modifiers() & Qt.ShiftModifier) or
                (QApplication.keyboardModifiers() & Qt.ShiftModifier)
            )
            self.node_scene.finish_wire_drag(sp, is_shift=is_shift)

        super().mouseReleaseEvent(event)

    def slice_wires(self, cut_path: QPainterPath) -> None:
        stroker = QPainterPathStroker()
        stroker.setWidth(8.0)
        cut_shape = stroker.createStroke(cut_path)

        wires_to_cut = []
        for wire in list(self.node_scene.wire_items.values()):
            wire_stroker = QPainterPathStroker()
            wire_stroker.setWidth(6.0)
            wire_shape = wire_stroker.createStroke(wire.path())
            if cut_shape.intersects(wire_shape):
                wires_to_cut.append(wire)

        if not wires_to_cut:
            return

        affected_nodes: Set[NodeBase] = set()
        for wire in wires_to_cut:
            conn = wire.connection
            affected_nodes.add(conn.target.node)
            self.node_scene.graph.disconnect(conn.source, conn.target)
            if wire in self.node_scene.items():
                self.node_scene.removeItem(wire)
            if conn.id in self.node_scene.wire_items:
                del self.node_scene.wire_items[conn.id]

        for node in affected_nodes:
            if hasattr(node, "sync_dynamic_ports"):
                if node.sync_dynamic_ports():
                    node_item = self.node_scene.node_items.get(node.id)
                    if node_item:
                        node_item.rebuild_ports()

        self.node_scene.notify_graph_changed()

    def wheelEvent(self, event: QWheelEvent) -> None:
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item = self.itemAt(pos)
        if isinstance(item, QGraphicsProxyWidget):
            super().wheelEvent(event)
            if event.isAccepted():
                return

        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
        event.accept()

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
        # Don't intercept shortcut keys if an embedded widget has keyboard focus
        focus_item = self.scene().focusItem()
        if isinstance(focus_item, QGraphicsProxyWidget) or (focus_item and hasattr(focus_item, "isWidget") and focus_item.isWidget()):
            super().keyPressEvent(event)
            return

        fw = QApplication.focusWidget()
        if fw is not None and fw not in (self, self.viewport()):
            super().keyPressEvent(event)
            return

        # Check if any embedded widget in selected items has focus
        for it in self.node_scene.selectedItems():
            if isinstance(it, NodeItem):
                for child in it.childItems():
                    if isinstance(child, QGraphicsProxyWidget):
                        w = child.widget()
                        if w and (w.hasFocus() or any(c.hasFocus() for c in w.findChildren(QWidget))):
                            super().keyPressEvent(event)
                            return

        # Check if an editable text widget currently has focus (e.g. QLineEdit, QPlainTextEdit)
        focus_widget = QApplication.focusWidget()
        if focus_widget and (hasattr(focus_widget, "text") or hasattr(focus_widget, "toPlainText")):
            super().keyPressEvent(event)
            return

        # Check if scene focus item is an embedded proxy widget
        if self.node_scene.focusItem() and isinstance(self.node_scene.focusItem(), QGraphicsProxyWidget):
            super().keyPressEvent(event)
            return

        # Ctrl+C: Copy selected nodes
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_C:
            self.copy_selected_nodes()
            event.accept()
            return

        # Ctrl+V: Paste copied nodes
        elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_V:
            self.paste_copied_nodes()
            event.accept()
            return

        elif event.key() == Qt.Key_Space or event.key() == Qt.Key_Tab:
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

    def copy_selected_nodes(self) -> None:
        selected_node_items = [it for it in self.node_scene.selectedItems() if isinstance(it, NodeItem)]
        if not selected_node_items:
            return

        copied_nodes = []
        selected_ids = set()
        for item in selected_node_items:
            data = item.node.serialize()
            copied_nodes.append(data)
            selected_ids.add(item.node.id)

        # Copy internal connections strictly between selected nodes
        copied_conns = []
        for conn in self.node_scene.graph.connections:
            if conn.source.node.id in selected_ids and conn.target.node.id in selected_ids:
                copied_conns.append({
                    "source_node": conn.source.node.id,
                    "source_port": conn.source.name,
                    "target_node": conn.target.node.id,
                    "target_port": conn.target.name
                })

        self._clipboard = {
            "nodes": copied_nodes,
            "connections": copied_conns
        }
        self._paste_offset = 35.0

    def paste_copied_nodes(self) -> None:
        clipboard = getattr(self, "_clipboard", None)
        if not clipboard or not clipboard.get("nodes"):
            return

        self.node_scene.clearSelection()

        id_map: Dict[str, NodeBase] = {}
        offset = getattr(self, "_paste_offset", 35.0)

        for n_data in clipboard["nodes"]:
            cls_name = n_data.get("type", "")
            cls = NODE_REGISTRY.get(cls_name)
            if not cls:
                continue

            new_node = cls()
            new_node.deserialize(n_data)
            new_node.x = float(n_data.get("x", 0.0)) + offset
            new_node.y = float(n_data.get("y", 0.0)) + offset

            item = self.node_scene.add_node_to_scene(new_node)
            item.setSelected(True)
            id_map[n_data["id"]] = new_node

        # Re-wire internal connections between pasted nodes
        for c_data in clipboard.get("connections", []):
            src_node = id_map.get(c_data["source_node"])
            tgt_node = id_map.get(c_data["target_node"])
            if src_node and tgt_node:
                src_port = next((p for p in src_node.outputs if p.name == c_data["source_port"]), None)
                if not src_port:
                    src_port = next((p for p in src_node.outputs if getattr(p, "original_name", None) == c_data["source_port"]), None)

                tgt_port = next((p for p in tgt_node.inputs if p.name == c_data["target_port"]), None)
                if not tgt_port:
                    tgt_port = next((p for p in tgt_node.inputs if getattr(p, "original_name", None) == c_data["target_port"]), None)

                if src_port and tgt_port:
                    conn = self.node_scene.graph.connect(src_port, tgt_port, append=True)
                    if conn:
                        src_item = self.node_scene.find_port_item(src_port)
                        dst_item = self.node_scene.find_port_item(tgt_port)
                        if src_item and dst_item:
                            wire = WireItem(conn, src_item, dst_item)
                            self.node_scene.addItem(wire)
                            self.node_scene.wire_items[conn.id] = wire

        for node in id_map.values():
            if hasattr(node, "sync_dynamic_ports"):
                if node.sync_dynamic_ports():
                    node_item = self.node_scene.node_items.get(node.id)
                    if node_item:
                        node_item.rebuild_ports()

        self._paste_offset = offset + 35.0
        self.node_scene.notify_graph_changed()

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
