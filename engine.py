# SPDX-License-Identifier: GPL-3.0-or-later
"""Core Node Graph engine, DAG solver, and serialization."""
from __future__ import annotations

import enum
import time
import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable, Set

log = logging.getLogger("ingetrazo.plugins.node_editor")


class PortType(enum.Enum):
    ANY = "any"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    STRING = "string"
    VECTOR = "vector"
    POINT = "point"
    CURVE = "curve"
    MESH = "mesh"


# Color mapping for visual port types
PORT_COLORS = {
    PortType.ANY: "#d4d4d4",
    PortType.NUMBER: "#4fc1ff",
    PortType.INTEGER: "#569cd6",
    PortType.BOOLEAN: "#c586c0",
    PortType.STRING: "#ce9178",
    PortType.VECTOR: "#4ec9b0",
    PortType.POINT: "#6a9955",
    PortType.CURVE: "#dcdcaa",
    PortType.MESH: "#f28b25",
}


class Port:
    """An input or output connection pin on a node."""

    def __init__(
        self,
        node: NodeBase,
        name: str,
        port_type: PortType = PortType.ANY,
        is_input: bool = True,
        default_value: Any = None,
        description: str = ""
    ):
        self.node = node
        self.name = name
        self.port_type = port_type
        self.is_input = is_input
        self._default_value = default_value
        self._value: Any = default_value
        self.description = description
        self.connections: List[Connection] = []

    @property
    def default_value(self) -> Any:
        return self._default_value

    @default_value.setter
    def default_value(self, val: Any) -> None:
        if self._value == self._default_value or self._value is None:
            self._value = val
        self._default_value = val

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, val: Any) -> None:
        self._value = val

    @property
    def has_connection(self) -> bool:
        return len(self.connections) > 0

    def get_color(self) -> str:
        return PORT_COLORS.get(self.port_type, "#d4d4d4")


class Connection:
    """A directed wire between an output port and an input port."""

    def __init__(self, source_port: Port, target_port: Port):
        self.id = str(uuid.uuid4())
        self.source = source_port  # Output
        self.target = target_port  # Input

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "source_node": self.source.node.id,
            "source_port": self.source.name,
            "target_node": self.target.node.id,
            "target_port": self.target.name
        }


class NodeBase:
    """Base class for all functional graph nodes."""

    name: str = "BaseNode"
    category: str = "General"
    description: str = ""
    header_color: str = "#3b4252"

    def __init__(self, node_id: Optional[str] = None):
        self.id = node_id or str(uuid.uuid4())
        self.name: str = self.__class__.name
        self.x: float = 0.0
        self.y: float = 0.0
        self.inputs: List[Port] = []
        self.outputs: List[Port] = []
        self.widget_values: Dict[str, Any] = {}
        self.dirty: bool = True
        self.error: Optional[str] = None
        self.setup_ports()

    def setup_ports(self) -> None:
        """Override to add input and output ports."""
        pass

    def add_input(
        self,
        name: str,
        port_type: PortType = PortType.ANY,
        default_value: Any = None,
        description: str = ""
    ) -> Port:
        p = Port(self, name, port_type, is_input=True, default_value=default_value, description=description)
        self.inputs.append(p)
        return p

    def add_output(
        self,
        name: str,
        port_type: PortType = PortType.ANY,
        description: str = ""
    ) -> Port:
        p = Port(self, name, port_type, is_input=False, default_value=None, description=description)
        self.outputs.append(p)
        return p

    def get_input(self, index_or_name: Any, fallback: Any = None) -> Any:
        port: Optional[Port] = None
        if isinstance(index_or_name, int) and 0 <= index_or_name < len(self.inputs):
            port = self.inputs[index_or_name]
        elif isinstance(index_or_name, str):
            for p in self.inputs:
                if p.name == index_or_name:
                    port = p
                    break

        if port is None:
            return fallback

        if port.has_connection:
            if len(port.connections) == 1:
                src = port.connections[0].source
                return src.value if src.value is not None else fallback
            else:
                merged = []
                for c in port.connections:
                    val = c.source.value
                    if isinstance(val, (list, tuple)):
                        merged.extend(val)
                    elif val is not None:
                        merged.append(val)
                return merged if merged else fallback

        # If disconnected, check widget value matching port name
        if port.name in self.widget_values:
            return self.widget_values[port.name]

        if port.value is not None:
            return port.value

        return port.default_value if port.default_value is not None else fallback

    def set_output(self, index_or_name: Any, value: Any) -> None:
        if isinstance(index_or_name, int) and 0 <= index_or_name < len(self.outputs):
            self.outputs[index_or_name].value = value
        elif isinstance(index_or_name, str):
            for p in self.outputs:
                if p.name == index_or_name:
                    p.value = value
                    break

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Core execution logic. Subclasses must implement."""
        pass

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "type": self.__class__.__name__,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "widgets": self.widget_values
        }

    def deserialize(self, data: dict) -> None:
        if "name" in data:
            self.name = str(data["name"])
        self.x = data.get("x", 0.0)
        self.y = data.get("y", 0.0)
        self.widget_values.update(data.get("widgets", {}))


class NodeGraph:
    """Container and solver for nodes and connections."""

    def __init__(self):
        self.nodes: List[NodeBase] = []
        self.connections: List[Connection] = []
        self.listeners: List[Callable[[], None]] = []
        self.is_evaluating: bool = False

    def add_node(self, node: NodeBase) -> NodeBase:
        if node not in self.nodes:
            self.nodes.append(node)
            self.notify_changed()
        return node

    def remove_node(self, node: NodeBase) -> None:
        if node in self.nodes:
            # Disconnect all wires attached to this node
            for conn in list(self.connections):
                if conn.source.node == node or conn.target.node == node:
                    self.disconnect(conn.source, conn.target)
            self.nodes.remove(node)
            self.notify_changed()

    def connect(self, source_port: Port, target_port: Port, append: bool = False) -> Optional[Connection]:
        if source_port.is_input or not target_port.is_input:
            return None
        if source_port.node == target_port.node:
            return None  # No self-loops

        # Prevent duplicate connection from the exact same source port
        for existing in target_port.connections:
            if existing.source == source_port:
                return existing

        if not append:
            # Single connection per input port if not appending
            for existing in list(target_port.connections):
                self.disconnect(existing.source, existing.target)

        conn = Connection(source_port, target_port)
        source_port.connections.append(conn)
        target_port.connections.append(conn)
        self.connections.append(conn)
        target_port.node.dirty = True
        self.notify_changed()
        return conn

    def disconnect(self, source_port: Port, target_port: Port) -> None:
        for conn in list(self.connections):
            if conn.source == source_port and conn.target == target_port:
                if conn in source_port.connections:
                    source_port.connections.remove(conn)
                if conn in target_port.connections:
                    target_port.connections.remove(conn)
                self.connections.remove(conn)
                target_port.node.dirty = True
                self.notify_changed()
                break

    def notify_changed(self) -> None:
        for cb in self.listeners:
            try:
                cb()
            except Exception as e:
                log.error(f"Error in graph change listener: {e}")

    def topological_sort(self) -> List[NodeBase]:
        """Order nodes so that producers execute before consumers."""
        in_degree: Dict[NodeBase, int] = {node: 0 for node in self.nodes}
        adj: Dict[NodeBase, List[NodeBase]] = {node: [] for node in self.nodes}

        for conn in self.connections:
            src_node = conn.source.node
            dst_node = conn.target.node
            if src_node in adj and dst_node in in_degree:
                adj[src_node].append(dst_node)
                in_degree[dst_node] += 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        sorted_nodes: List[NodeBase] = []

        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Include disconnected / cycle leftovers
        for node in self.nodes:
            if node not in sorted_nodes:
                sorted_nodes.append(node)

        return sorted_nodes

    def evaluate(self, context: Optional[Dict[str, Any]] = None) -> float:
        """Execute the graph in topological order. Returns elapsed ms."""
        t0 = time.perf_counter()
        self.is_evaluating = True

        order = self.topological_sort()
        for node in order:
            node.error = None
            try:
                node.compute(context=context)
                node.dirty = False
            except Exception as ex:
                node.error = str(ex)
                log.warning(f"Error computing node {node.name} ({node.id}): {ex}")

        self.is_evaluating = False
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return elapsed_ms

    def serialize(self) -> dict:
        return {
            "version": 1,
            "nodes": [n.serialize() for n in self.nodes],
            "connections": [c.serialize() for c in self.connections]
        }

    def deserialize(self, data: dict, node_registry: Dict[str, type]) -> None:
        self.connections.clear()
        self.nodes.clear()

        id_map: Dict[str, NodeBase] = {}
        for nd in data.get("nodes", []):
            ntype = nd.get("type")
            cls = node_registry.get(ntype)
            if cls:
                node = cls(node_id=nd.get("id"))
                node.deserialize(nd)
                self.nodes.append(node)
                id_map[node.id] = node

        for cd in data.get("connections", []):
            src_node = id_map.get(cd.get("source_node"))
            dst_node = id_map.get(cd.get("target_node"))
            if src_node and dst_node:
                src_port = next((p for p in src_node.outputs if p.name == cd.get("source_port")), None)
                dst_port = next((p for p in dst_node.inputs if p.name == cd.get("target_port")), None)
                if src_port and dst_port:
                    self.connect(src_port, dst_port)

        self.notify_changed()
