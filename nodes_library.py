# SPDX-License-Identifier: GPL-3.0-or-later
"""Comprehensive catalog of parametric modeling nodes for IngeTrazo."""
from __future__ import annotations

import ast
import math
import copy
from typing import List, Dict, Any, Optional, Union

from .engine import NodeBase, PortType
from .models import (
    Point3D, Vector3D, PolylineData, FaceData, EdgeData, MeshData,
    create_box, create_cylinder, create_sphere, extrude_profile
)

# Registry of all available nodes: {Class.__name__: Class}
NODE_REGISTRY: Dict[str, type] = {}


def register_node(cls: type) -> type:
    NODE_REGISTRY[cls.__name__] = cls
    return cls


def _safe_ln(v: float) -> float:
    try:
        fv = float(v)
        if fv > 1e-15:
            return math.log(fv)
        elif fv < -1e-15:
            return math.log(abs(fv))
        return -34.54
    except Exception:
        return 0.0


def _safe_log(v: float, base: Optional[float] = None) -> float:
    try:
        fv = float(v)
        val = fv if fv > 1e-15 else (abs(fv) if abs(fv) > 1e-15 else 1e-15)
        if base is not None:
            return math.log(val, float(base))
        return math.log(val)
    except Exception:
        return 0.0


def _safe_sqrt(v: float) -> float:
    try:
        fv = float(v)
        return math.sqrt(fv if fv >= 0 else abs(fv))
    except Exception:
        return 0.0


def _safe_asin(v: float) -> float:
    try:
        return math.asin(max(-1.0, min(1.0, float(v))))
    except Exception:
        return 0.0


def _safe_acos(v: float) -> float:
    try:
        return math.acos(max(-1.0, min(1.0, float(v))))
    except Exception:
        return 0.0


# Safe evaluation environment for math expressions
MATH_ENV: Dict[str, Any] = {
    # Constants
    "pi": math.pi,
    "PI": math.pi,
    "e": math.e,
    "E": math.e,
    "tau": math.tau,
    "TAU": math.tau,
    "phi": (1.0 + math.sqrt(5.0)) / 2.0,
    # Trigonometric functions
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": _safe_asin,
    "acos": _safe_acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "SIN": math.sin,
    "COS": math.cos,
    "TAN": math.tan,
    # Logarithmic & Exponential
    "ln": _safe_ln,
    "LN": _safe_ln,
    "log": _safe_log,
    "LOG": _safe_log,
    "log10": (lambda v: math.log10(v if v > 1e-15 else (abs(v) if abs(v) > 1e-15 else 1e-15))),
    "LOG10": (lambda v: math.log10(v if v > 1e-15 else (abs(v) if abs(v) > 1e-15 else 1e-15))),
    "log2": (lambda v: math.log2(v if v > 1e-15 else (abs(v) if abs(v) > 1e-15 else 1e-15))),
    "LOG2": (lambda v: math.log2(v if v > 1e-15 else (abs(v) if abs(v) > 1e-15 else 1e-15))),
    "exp": math.exp,
    "EXP": math.exp,
    # Powers & Roots
    "sqrt": _safe_sqrt,
    "SQRT": _safe_sqrt,
    "cbrt": (lambda v: math.copysign(abs(v) ** (1.0 / 3.0), v)),
    "pow": pow,
    "sq": (lambda v: float(v) * float(v)),
    # Rounding & Signs
    "abs": abs,
    "ABS": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "min": min,
    "max": max,
    "clamp": (lambda v, mn, mx: max(mn, min(mx, v))),
    "lerp": (lambda a, b, t: a + (b - a) * t),
    # Geometric utilities
    "hypot": math.hypot,
    "deg": math.degrees,
    "rad": math.radians,
    "degrees": math.degrees,
    "radians": math.radians,
}

_EXPR_CACHE: Dict[str, Any] = {}


def _prepare_expression(expr_str: str) -> str:
    """Normalize mathematical expression syntax for Python evaluation."""
    s = expr_str.strip()
    s = s.replace("^", "**")
    return s


def _safe_compile(expr_str: str):
    """Compile an expression string safely after validating AST nodes."""
    clean = _prepare_expression(expr_str)
    if clean in _EXPR_CACHE:
        return _EXPR_CACHE[clean]

    tree = ast.parse(clean, mode="eval")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute)):
            raise ValueError("Imports and attribute accesses are forbidden in expressions")
        if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
            raise ValueError("Only direct math function calls are allowed")

    code = compile(tree, "<expression>", "eval")
    _EXPR_CACHE[clean] = code
    return code


# =====================================================================================
# 1. INPUT NODES
# =====================================================================================

@register_node
class NumberSliderNode(NodeBase):
    name = "Number Slider"
    category = "Input"
    description = "Interactive numeric slider emitting a floating-point value."
    header_color = "#205493"

    def setup_ports(self) -> None:
        self.add_output("Value", PortType.NUMBER, "Output number")
        self.widget_values.setdefault("value", 5.0)
        self.widget_values.setdefault("min", 0.0)
        self.widget_values.setdefault("max", 50.0)
        self.widget_values.setdefault("step", 0.1)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        val = float(self.widget_values.get("value", 0.0))
        self.set_output("Value", val)


@register_node
class IntegerSliderNode(NodeBase):
    name = "Integer Slider"
    category = "Input"
    description = "Interactive slider emitting an integer value."
    header_color = "#205493"

    def setup_ports(self) -> None:
        self.add_output("Value", PortType.INTEGER, "Output integer")
        self.widget_values.setdefault("value", 10)
        self.widget_values.setdefault("min", 1)
        self.widget_values.setdefault("max", 100)
        self.widget_values.setdefault("step", 1)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        val = int(round(float(self.widget_values.get("value", 1))))
        self.set_output("Value", val)


@register_node
class ToggleNode(NodeBase):
    name = "Toggle (Boolean)"
    category = "Input"
    description = "True/False switch toggle."
    header_color = "#205493"

    def setup_ports(self) -> None:
        self.add_output("Value", PortType.BOOLEAN, "Output boolean")
        self.widget_values.setdefault("value", True)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        self.set_output("Value", bool(self.widget_values.get("value", True)))


@register_node
class VectorInputNode(NodeBase):
    name = "Vector XYZ"
    category = "Input"
    description = "Construct a 3D directional vector from X, Y, Z numbers."
    header_color = "#205493"

    def setup_ports(self) -> None:
        self.add_input("X", PortType.NUMBER, 0.0)
        self.add_input("Y", PortType.NUMBER, 0.0)
        self.add_input("Z", PortType.NUMBER, 1.0)
        self.add_output("Vector", PortType.VECTOR, "3D vector")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        x = float(self.get_input("X", 0.0))
        y = float(self.get_input("Y", 0.0))
        z = float(self.get_input("Z", 1.0))
        self.set_output("Vector", Vector3D(x, y, z))


@register_node
class StringNode(NodeBase):
    name = "Text"
    category = "Input"
    description = "Text string constant (for names, layers, materials)."
    header_color = "#205493"

    def setup_ports(self) -> None:
        self.add_output("Text", PortType.STRING, "Output text")
        self.widget_values.setdefault("value", "Parametric")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        self.set_output("Text", str(self.widget_values.get("value", "")))


def format_panel_value(val: Any, max_items: int = 150) -> str:
    """Format any data structure for display inside a Panel node."""
    if val is None:
        return "None"

    # Point3D
    if isinstance(val, Point3D):
        return f"Point3D({val.x:.3f}, {val.y:.3f}, {val.z:.3f})"

    # Vector3D
    if isinstance(val, Vector3D):
        return f"Vector3D({val.x:.3f}, {val.y:.3f}, {val.z:.3f})"

    # MeshData
    if isinstance(val, MeshData):
        f_cnt = len(val.faces)
        e_cnt = len(val.edges)
        name_str = f" '{val.name}'" if val.name else ""
        return f"MeshData{name_str} ({f_cnt} faces, {e_cnt} edges)"

    # PolylineData
    if isinstance(val, PolylineData):
        closed_str = "closed" if val.closed else "open"
        return f"Polyline ({len(val.points)} pts, {closed_str})"

    # FaceData
    if isinstance(val, FaceData):
        return f"Face ({len(val.vertices)} vertices)"

    # EdgeData
    if isinstance(val, EdgeData):
        return f"Edge ({val.start} -> {val.end})"

    # Lists or tuples
    if isinstance(val, (list, tuple)):
        if len(val) == 0:
            return "[Empty List]"

        lines: List[str] = []
        show_count = min(len(val), max_items)
        for i in range(show_count):
            item = val[i]
            formatted_item = _format_single_item(item)
            lines.append(f"[{i}] {formatted_item}")

        if len(val) > max_items:
            lines.append(f"... ({len(val) - max_items} more items, total {len(val)})")

        return "\n".join(lines)

    # Boolean
    if isinstance(val, bool):
        return str(val)

    # Integer
    if isinstance(val, int):
        return str(val)

    # Float
    if isinstance(val, float):
        formatted = f"{val:.4f}".rstrip("0").rstrip(".")
        return formatted if formatted != "-0" else "0"

    # String or other
    return str(val)


def _format_single_item(item: Any) -> str:
    """Format an individual element within a list for compact panel display."""
    if item is None:
        return "None"
    if isinstance(item, Point3D):
        return f"Point3D({item.x:.2f}, {item.y:.2f}, {item.z:.2f})"
    if isinstance(item, Vector3D):
        return f"Vector3D({item.x:.2f}, {item.y:.2f}, {item.z:.2f})"
    if isinstance(item, MeshData):
        return f"Mesh ({len(item.faces)} faces, {len(item.edges)} edges)"
    if isinstance(item, PolylineData):
        return f"Polyline ({len(item.points)} pts)"
    if isinstance(item, (list, tuple)):
        return f"List ({len(item)} items)"
    if isinstance(item, float):
        formatted = f"{item:.4f}".rstrip("0").rstrip(".")
        return formatted if formatted != "-0" else "0"
    return str(item)


def parse_panel_input(text: str) -> Any:
    """Parse text entered into a disconnected Panel node."""
    if not text or not text.strip():
        return ""

    raw_lines = [ln.strip() for ln in text.splitlines()]
    non_empty = [ln for ln in raw_lines if ln]

    if not non_empty:
        return ""

    parsed_items: List[Any] = []
    for line in non_empty:
        low = line.lower()
        if low == "true":
            parsed_items.append(True)
        elif low == "false":
            parsed_items.append(False)
        else:
            try:
                parsed_items.append(int(line))
                continue
            except ValueError:
                pass
            try:
                parsed_items.append(float(line))
                continue
            except ValueError:
                pass
            parsed_items.append(line)

    if len(raw_lines) == 1 and "\n" not in text and "\r" not in text:
        return parsed_items[0]
    return parsed_items


@register_node
class PanelNode(NodeBase):
    name = "Panel"
    category = "Input"
    description = "Inspect and view any data (numbers, points, lists, meshes) with indexed output, or enter multiline text and constants."
    header_color = "#ebcb8b"

    def __init__(self, node_id: Optional[str] = None):
        self.on_display_updated: Optional[Any] = None
        super().__init__(node_id)

    def setup_ports(self) -> None:
        self.add_input("Data", PortType.ANY, description="Incoming data to inspect/view")
        self.add_output("Data", PortType.ANY, description="Pass-through data or entered text/numbers")
        self.widget_values.setdefault("text", "")
        self.widget_values.setdefault("display", "")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        self.error = None
        data_port = self.inputs[0] if self.inputs else None

        if data_port and data_port.has_connection:
            src_val = self.get_input("Data")
            self.set_output("Data", src_val)
            display_str = format_panel_value(src_val)
            self.widget_values["display"] = display_str
            if self.on_display_updated:
                try:
                    self.on_display_updated(display_str)
                except Exception:
                    pass
        else:
            text = str(self.widget_values.get("text", ""))
            parsed = parse_panel_input(text)
            self.set_output("Data", parsed)
            self.widget_values["display"] = text
            if self.on_display_updated:
                try:
                    self.on_display_updated(text)
                except Exception:
                    pass


# =====================================================================================
# 2. MATH NODES
# =====================================================================================

@register_node
class AddNode(NodeBase):
    name = "Add"
    category = "Math"
    description = "Add two numbers (A + B)."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.NUMBER, 0.0)
        self.add_input("B", PortType.NUMBER, 0.0)
        self.add_output("Result", PortType.NUMBER)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a = float(self.get_input("A", 0.0))
        b = float(self.get_input("B", 0.0))
        self.set_output("Result", a + b)


@register_node
class SubtractNode(NodeBase):
    name = "Subtract"
    category = "Math"
    description = "Subtract two numbers (A - B)."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.NUMBER, 0.0)
        self.add_input("B", PortType.NUMBER, 0.0)
        self.add_output("Result", PortType.NUMBER)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a = float(self.get_input("A", 0.0))
        b = float(self.get_input("B", 0.0))
        self.set_output("Result", a - b)


@register_node
class MultiplyNode(NodeBase):
    name = "Multiply"
    category = "Math"
    description = "Multiply two numbers (A * B)."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.NUMBER, 1.0)
        self.add_input("B", PortType.NUMBER, 1.0)
        self.add_output("Result", PortType.NUMBER)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a = float(self.get_input("A", 1.0))
        b = float(self.get_input("B", 1.0))
        self.set_output("Result", a * b)


@register_node
class DivideNode(NodeBase):
    name = "Divide"
    category = "Math"
    description = "Divide two numbers (A / B)."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.NUMBER, 1.0)
        self.add_input("B", PortType.NUMBER, 1.0)
        self.add_output("Result", PortType.NUMBER)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a = float(self.get_input("A", 1.0))
        b = float(self.get_input("B", 1.0))
        self.set_output("Result", a / b if abs(b) > 1e-12 else 0.0)


@register_node
class RangeSeriesNode(NodeBase):
    name = "Series / Range"
    category = "Math"
    description = "Generate a series of numbers [Start, Start + Step, ...]."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("Start", PortType.NUMBER, 0.0)
        self.add_input("Step", PortType.NUMBER, 1.0)
        self.add_input("Count", PortType.INTEGER, 10)
        self.add_output("List", PortType.ANY, "List of numbers")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        start = float(self.get_input("Start", 0.0))
        step = float(self.get_input("Step", 1.0))
        count = max(1, int(self.get_input("Count", 10)))
        series = [start + i * step for i in range(count)]
        self.set_output("List", series)


@register_node
class DivideRangeNode(NodeBase):
    name = "Divide Range"
    category = "Math"
    description = "Divide a domain [Start, End] into evenly spaced numbers using Count (Linear Space / Linspace)."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("Start", PortType.NUMBER, 0.0, "Start value of domain")
        self.add_input("End", PortType.NUMBER, 1.0, "End value of domain")
        self.add_input("Count", PortType.INTEGER, 10, "Number of steps / points in range")
        self.add_output("List", PortType.ANY, "Evenly spaced list of numbers")
        self.add_output("Step", PortType.NUMBER, "Step size between adjacent values")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        s_in = self.get_input("Start", 0.0)
        e_in = self.get_input("End", 1.0)
        c_in = self.get_input("Count", 10)

        is_list = any(isinstance(v, (list, tuple)) for v in [s_in, e_in, c_in])
        if not is_list:
            try:
                start = float(s_in)
            except Exception:
                start = 0.0
            try:
                end = float(e_in)
            except Exception:
                end = 1.0
            try:
                count = max(1, int(c_in))
            except Exception:
                count = 10

            if count == 1:
                self.set_output("List", [start])
                self.set_output("Step", 0.0)
            else:
                step = (end - start) / (count - 1)
                series = [(start + i * step) for i in range(count - 1)] + [end]
                self.set_output("List", series)
                self.set_output("Step", step)
        else:
            starts = s_in if isinstance(s_in, (list, tuple)) else [s_in]
            ends = e_in if isinstance(e_in, (list, tuple)) else [e_in]
            counts = c_in if isinstance(c_in, (list, tuple)) else [c_in]
            n_items = max(len(starts), len(ends), len(counts))

            all_series: List[List[float]] = []
            all_steps: List[float] = []
            for i in range(n_items):
                try:
                    st = float(starts[min(i, len(starts) - 1)])
                except Exception:
                    st = 0.0
                try:
                    en = float(ends[min(i, len(ends) - 1)])
                except Exception:
                    en = 1.0
                try:
                    cnt = max(1, int(counts[min(i, len(counts) - 1)]))
                except Exception:
                    cnt = 10

                if cnt == 1:
                    all_series.append([st])
                    all_steps.append(0.0)
                else:
                    stp = (en - st) / (cnt - 1)
                    s = [(st + j * stp) for j in range(cnt - 1)] + [en]
                    all_series.append(s)
                    all_steps.append(stp)

            if len(all_series) == 1:
                self.set_output("List", all_series[0])
                self.set_output("Step", all_steps[0])
            else:
                self.set_output("List", all_series)
                self.set_output("Step", all_steps)


@register_node
class ExpressionNode(NodeBase):
    name = "Expression"
    category = "Math"
    description = "Evaluate mathematical expressions (e.g. sin(x)*cos(y), x^2 + y^2, sqrt(x*x + y*y)). Supports lists, broadcasting, and trigonometry."
    header_color = "#b48ead"

    def setup_ports(self) -> None:
        self.add_input("x", PortType.ANY, 1.0, "Input variable x (or u, a)")
        self.add_input("y", PortType.ANY, 1.0, "Input variable y (or v, b)")
        self.add_input("z", PortType.ANY, 0.0, "Input variable z (or w, c)")
        self.add_input("Expr", PortType.STRING, "", "Formula override wire")
        self.add_output("Result", PortType.ANY, "Evaluated result (number or list)")
        self.widget_values.setdefault("expr", "x + y")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        self.error = None
        # Wire input overrides on-node widget if provided and non-empty
        wire_expr = self.get_input("Expr", "")
        if wire_expr and str(wire_expr).strip():
            expr_str = str(wire_expr).strip()
        else:
            expr_str = str(self.widget_values.get("expr", "x + y")).strip()

        if not expr_str:
            self.set_output("Result", 0.0)
            return

        try:
            code = _safe_compile(expr_str)
        except Exception as ex:
            self.error = f"Expression syntax error: {ex}"
            self.set_output("Result", 0.0)
            return

        x_raw = self.get_input("x", 1.0)
        y_raw = self.get_input("y", 1.0)
        z_raw = self.get_input("z", 0.0)

        # Check if any input is a list/tuple
        is_x_list = isinstance(x_raw, (list, tuple))
        is_y_list = isinstance(y_raw, (list, tuple))
        is_z_list = isinstance(z_raw, (list, tuple))

        has_list = is_x_list or is_y_list or is_z_list

        if has_list:
            len_x = len(x_raw) if is_x_list else 1
            len_y = len(y_raw) if is_y_list else 1
            len_z = len(z_raw) if is_z_list else 1
            n_items = max(len_x, len_y, len_z)

            results: List[float] = []
            for i in range(n_items):
                try:
                    val_x = float(x_raw[i % len_x]) if is_x_list else float(x_raw)
                except Exception:
                    val_x = 0.0
                try:
                    val_y = float(y_raw[i % len_y]) if is_y_list else float(y_raw)
                except Exception:
                    val_y = 0.0
                try:
                    val_z = float(z_raw[i % len_z]) if is_z_list else float(z_raw)
                except Exception:
                    val_z = 0.0

                scope = dict(MATH_ENV)
                scope.update({
                    "x": val_x, "y": val_y, "z": val_z,
                    "X": val_x, "Y": val_y, "Z": val_z,
                    "u": val_x, "v": val_y, "w": val_z,
                    "U": val_x, "V": val_y, "W": val_z,
                    "a": val_x, "b": val_y, "c": val_z,
                    "A": val_x, "B": val_y, "C": val_z,
                    "i": float(i),
                })
                try:
                    res = eval(code, {"__builtins__": {}}, scope)
                    results.append(float(res))
                except Exception as ex:
                    self.error = f"Eval error at [{i}]: {ex}"
                    results.append(0.0)

            self.set_output("Result", results)
        else:
            try:
                val_x = float(x_raw)
            except Exception:
                val_x = 0.0
            try:
                val_y = float(y_raw)
            except Exception:
                val_y = 0.0
            try:
                val_z = float(z_raw)
            except Exception:
                val_z = 0.0

            scope = dict(MATH_ENV)
            scope.update({
                "x": val_x, "y": val_y, "z": val_z,
                "X": val_x, "Y": val_y, "Z": val_z,
                "u": val_x, "v": val_y, "w": val_z,
                "U": val_x, "V": val_y, "W": val_z,
                "a": val_x, "b": val_y, "c": val_z,
                "A": val_x, "B": val_y, "C": val_z,
                "i": 0.0,
            })
            try:
                res = eval(code, {"__builtins__": {}}, scope)
                self.set_output("Result", float(res))
            except Exception as ex:
                self.error = f"Eval error: {ex}"
                self.set_output("Result", 0.0)


# =====================================================================================
# 3. LIST UTILITIES
# =====================================================================================

@register_node
class CrossReferenceNode(NodeBase):
    name = "Cross Reference"
    category = "List"
    description = "Compute the Cartesian product of two lists (A × B) to cross-reference every item of A with every item of B."
    header_color = "#5e81ac"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.ANY, description="First list of items")
        self.add_input("B", PortType.ANY, description="Second list of items")
        self.add_output("A", PortType.ANY, description="Cross-referenced elements of list A")
        self.add_output("B", PortType.ANY, description="Cross-referenced elements of list B")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        raw_a = self.get_input("A")
        raw_b = self.get_input("B")

        if raw_a is None or raw_b is None:
            self.set_output("A", [])
            self.set_output("B", [])
            return

        list_a = list(raw_a) if isinstance(raw_a, (list, tuple)) else [raw_a]
        list_b = list(raw_b) if isinstance(raw_b, (list, tuple)) else [raw_b]

        if not list_a or not list_b:
            self.set_output("A", [])
            self.set_output("B", [])
            return

        out_a: List[Any] = []
        out_b: List[Any] = []

        for a in list_a:
            for b in list_b:
                out_a.append(a)
                out_b.append(b)

        self.set_output("A", out_a)
        self.set_output("B", out_b)


# =====================================================================================
# 4. VECTOR & POINTS
# =====================================================================================

@register_node
class ConstructPointNode(NodeBase):
    name = "Construct Point"
    category = "Point"
    description = "Create a 3D point (or list of points) from X, Y, Z coordinates."
    header_color = "#a3be8c"

    def setup_ports(self) -> None:
        self.add_input("X", PortType.ANY, 0.0)
        self.add_input("Y", PortType.ANY, 0.0)
        self.add_input("Z", PortType.ANY, 0.0)
        self.add_output("Point", PortType.POINT, "Constructed Point3D")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        x_in = self.get_input("X", 0.0)
        y_in = self.get_input("Y", 0.0)
        z_in = self.get_input("Z", 0.0)

        # If any input is a list, generate a list of points
        is_list = any(isinstance(v, (list, tuple)) for v in [x_in, y_in, z_in])
        if is_list:
            xs = x_in if isinstance(x_in, (list, tuple)) else [x_in]
            ys = y_in if isinstance(y_in, (list, tuple)) else [y_in]
            zs = z_in if isinstance(z_in, (list, tuple)) else [z_in]
            max_len = max(len(xs), len(ys), len(zs))
            pts = []
            for i in range(max_len):
                x = float(xs[min(i, len(xs) - 1)])
                y = float(ys[min(i, len(ys) - 1)])
                z = float(zs[min(i, len(zs) - 1)])
                pts.append(Point3D(x, y, z))
            self.set_output("Point", pts)
        else:
            self.set_output("Point", Point3D(float(x_in), float(y_in), float(z_in)))


@register_node
class DeconstructPointNode(NodeBase):
    name = "Deconstruct Point"
    category = "Point"
    description = "Break a Point3D into its X, Y, Z coordinate values."
    header_color = "#a3be8c"

    def setup_ports(self) -> None:
        self.add_input("Point", PortType.POINT)
        self.add_output("X", PortType.NUMBER)
        self.add_output("Y", PortType.NUMBER)
        self.add_output("Z", PortType.NUMBER)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        pt = self.get_input("Point")
        if isinstance(pt, Point3D):
            self.set_output("X", pt.x)
            self.set_output("Y", pt.y)
            self.set_output("Z", pt.z)
        elif isinstance(pt, (list, tuple)):
            if pt and isinstance(pt[0], Point3D):
                self.set_output("X", [p.x for p in pt if isinstance(p, Point3D)])
                self.set_output("Y", [p.y for p in pt if isinstance(p, Point3D)])
                self.set_output("Z", [p.z for p in pt if isinstance(p, Point3D)])
            elif len(pt) >= 3 and all(isinstance(v, (int, float)) for v in pt[:3]):
                self.set_output("X", float(pt[0]))
                self.set_output("Y", float(pt[1]))
                self.set_output("Z", float(pt[2]))


@register_node
class DistanceNode(NodeBase):
    name = "Distance"
    category = "Point"
    description = "Euclidean distance between Point A and Point B."
    header_color = "#a3be8c"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.POINT)
        self.add_input("B", PortType.POINT)
        self.add_output("Distance", PortType.NUMBER)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a_in = self.get_input("A", Point3D(0, 0, 0))
        b_in = self.get_input("B", Point3D(0, 0, 0))
        if isinstance(a_in, Point3D) and isinstance(b_in, Point3D):
            self.set_output("Distance", a_in.distance_to(b_in))
        elif isinstance(a_in, (list, tuple)) or isinstance(b_in, (list, tuple)):
            as_ = a_in if isinstance(a_in, (list, tuple)) else [a_in]
            bs_ = b_in if isinstance(b_in, (list, tuple)) else [b_in]
            cnt = max(len(as_), len(bs_))
            dists = []
            for i in range(cnt):
                pa = as_[min(i, len(as_) - 1)]
                pb = bs_[min(i, len(bs_) - 1)]
                if isinstance(pa, Point3D) and isinstance(pb, Point3D):
                    dists.append(pa.distance_to(pb))
                else:
                    dists.append(0.0)
            self.set_output("Distance", dists)


@register_node
class GridPointsNode(NodeBase):
    name = "Point Grid (2D)"
    category = "Point"
    description = "Generate an X-Y grid array of points."
    header_color = "#a3be8c"

    def setup_ports(self) -> None:
        self.add_input("Count X", PortType.INTEGER, 5)
        self.add_input("Count Y", PortType.INTEGER, 5)
        self.add_input("Step X", PortType.NUMBER, 1.0)
        self.add_input("Step Y", PortType.NUMBER, 1.0)
        self.add_output("Points", PortType.ANY, "List of Point3D")
        self.add_output("Mesh", PortType.MESH, "Point Markers Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        nx = max(1, int(self.get_input("Count X", 5)))
        ny = max(1, int(self.get_input("Count Y", 5)))
        dx = float(self.get_input("Step X", 1.0))
        dy = float(self.get_input("Step Y", 1.0))

        pts: List[Point3D] = []
        for j in range(ny):
            for i in range(nx):
                pts.append(Point3D(i * dx, j * dy, 0.0))
        self.set_output("Points", pts)
        self.set_output("Mesh", _to_mesh_data(pts))


# =====================================================================================
# 4. CURVES & PROFILES
# =====================================================================================

@register_node
class LineNode(NodeBase):
    name = "Line"
    category = "Curve"
    description = "Line segment connecting two points."
    header_color = "#ebcb8b"

    def setup_ports(self) -> None:
        self.add_input("A", PortType.POINT, Point3D(0, 0, 0))
        self.add_input("B", PortType.POINT, Point3D(1, 0, 0))
        self.add_output("Line", PortType.CURVE, "Line curve")
        self.add_output("Mesh", PortType.MESH, "Wireframe Edge Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a_in = self.get_input("A", Point3D(0, 0, 0))
        b_in = self.get_input("B", Point3D(1, 0, 0))

        as_ = a_in if isinstance(a_in, (list, tuple)) else [a_in]
        bs_ = b_in if isinstance(b_in, (list, tuple)) else [b_in]

        count = max(len(as_), len(bs_))
        all_lines: List[PolylineData] = []
        all_edges: List[EdgeData] = []

        for i in range(count):
            a = as_[min(i, len(as_) - 1)]
            b = bs_[min(i, len(bs_) - 1)]
            if isinstance(a, Point3D) and isinstance(b, Point3D):
                all_lines.append(PolylineData(points=[a, b], closed=False))
                all_edges.append(EdgeData(a, b))

        if len(all_lines) == 1:
            self.set_output("Line", all_lines[0])
        else:
            self.set_output("Line", all_lines)
        self.set_output("Mesh", MeshData(edges=all_edges, name="Line"))


@register_node
class RectangleNode(NodeBase):
    name = "Rectangle"
    category = "Curve"
    description = "Planar rectangle profile / face."
    header_color = "#ebcb8b"

    def setup_ports(self) -> None:
        self.add_input("Origin", PortType.POINT, Point3D(0, 0, 0))
        self.add_input("Width", PortType.NUMBER, 4.0)
        self.add_input("Length", PortType.NUMBER, 6.0)
        self.add_input("Centered", PortType.BOOLEAN, True)
        self.add_output("Profile", PortType.CURVE, "Closed 4-point polygon")
        self.add_output("Mesh", PortType.MESH, "Planar Face Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        orig_in = self.get_input("Origin", Point3D(0, 0, 0))
        w_in = self.get_input("Width", 4.0)
        l_in = self.get_input("Length", 6.0)
        centered = bool(self.get_input("Centered", True))

        if isinstance(orig_in, (list, tuple)):
            origins = [p for p in orig_in if isinstance(p, Point3D)]
        elif isinstance(orig_in, Point3D):
            origins = [orig_in]
        else:
            origins = [Point3D(0, 0, 0)]

        ws = w_in if isinstance(w_in, (list, tuple)) else [w_in]
        ls = l_in if isinstance(l_in, (list, tuple)) else [l_in]

        all_polylines: List[PolylineData] = []
        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []

        for idx, o in enumerate(origins):
            w = float(ws[min(idx, len(ws) - 1)])
            l = float(ls[min(idx, len(ls) - 1)])

            if centered:
                x0, x1 = o.x - w / 2, o.x + w / 2
                y0, y1 = o.y - l / 2, o.y + l / 2
            else:
                x0, x1 = o.x, o.x + w
                y0, y1 = o.y, o.y + l

            pts = [
                Point3D(x0, y0, o.z),
                Point3D(x1, y0, o.z),
                Point3D(x1, y1, o.z),
                Point3D(x0, y1, o.z),
            ]
            all_polylines.append(PolylineData(points=pts, closed=True))
            all_faces.append(FaceData(vertices=pts))
            all_edges.extend([EdgeData(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))])

        if len(all_polylines) == 1:
            self.set_output("Profile", all_polylines[0])
        else:
            self.set_output("Profile", all_polylines)
        self.set_output("Mesh", MeshData(faces=all_faces, edges=all_edges, name="Rectangle"))


@register_node
class CirclePolygonNode(NodeBase):
    name = "Circle / Polygon"
    category = "Curve"
    description = "Circular profile or regular n-gon."
    header_color = "#ebcb8b"

    def setup_ports(self) -> None:
        self.add_input("Center", PortType.POINT, Point3D(0, 0, 0))
        self.add_input("Radius", PortType.NUMBER, 2.0)
        self.add_input("Segments", PortType.INTEGER, 24)
        self.add_output("Profile", PortType.CURVE, "Circular polygon")
        self.add_output("Mesh", PortType.MESH, "Planar Face Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        center_in = self.get_input("Center", Point3D(0, 0, 0))
        r_in = self.get_input("Radius", 2.0)
        segs_in = self.get_input("Segments", 24)

        if isinstance(center_in, (list, tuple)):
            centers = [p for p in center_in if isinstance(p, Point3D)]
        elif isinstance(center_in, Point3D):
            centers = [center_in]
        else:
            centers = [Point3D(0, 0, 0)]

        radii = r_in if isinstance(r_in, (list, tuple)) else [r_in]
        segments = segs_in if isinstance(segs_in, (list, tuple)) else [segs_in]

        all_polylines: List[PolylineData] = []
        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []

        for idx, c in enumerate(centers):
            r = float(radii[min(idx, len(radii) - 1)])
            segs = max(3, int(segments[min(idx, len(segments) - 1)]))

            pts: List[Point3D] = []
            for i in range(segs):
                angle = 2.0 * math.pi * i / segs
                pts.append(Point3D(c.x + r * math.cos(angle), c.y + r * math.sin(angle), c.z))

            all_polylines.append(PolylineData(points=pts, closed=True))
            all_faces.append(FaceData(vertices=pts))
            all_edges.extend([EdgeData(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))])

        if len(all_polylines) == 1:
            self.set_output("Profile", all_polylines[0])
        else:
            self.set_output("Profile", all_polylines)
        self.set_output("Mesh", MeshData(faces=all_faces, edges=all_edges, name="Circle"))


# =====================================================================================
# 5. SOLIDS & 3D GEOMETRY
# =====================================================================================

@register_node
class BoxNode(NodeBase):
    name = "Box (Solid)"
    category = "Solids"
    description = "Parametric 6-sided solid box cuboid."
    header_color = "#b48ead"

    def setup_ports(self) -> None:
        self.add_input("Center", PortType.POINT, Point3D(0, 0, 0))
        self.add_input("Size X", PortType.NUMBER, 3.0)
        self.add_input("Size Y", PortType.NUMBER, 4.0)
        self.add_input("Size Z", PortType.NUMBER, 2.5)
        self.add_input("Centered", PortType.BOOLEAN, False)
        self.add_output("Mesh", PortType.MESH, "Solid Box Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        center_in = self.get_input("Center", Point3D(0, 0, 0))
        dx_in = self.get_input("Size X", 3.0)
        dy_in = self.get_input("Size Y", 4.0)
        dz_in = self.get_input("Size Z", 2.5)
        centered = bool(self.get_input("Centered", False))

        if isinstance(center_in, (list, tuple)):
            centers = [p for p in center_in if isinstance(p, Point3D)]
        elif isinstance(center_in, Point3D):
            centers = [center_in]
        else:
            centers = [Point3D(0, 0, 0)]

        dxs = dx_in if isinstance(dx_in, (list, tuple)) else [dx_in]
        dys = dy_in if isinstance(dy_in, (list, tuple)) else [dy_in]
        dzs = dz_in if isinstance(dz_in, (list, tuple)) else [dz_in]

        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []

        for idx, c in enumerate(centers):
            dx = float(dxs[min(idx, len(dxs) - 1)])
            dy = float(dys[min(idx, len(dys) - 1)])
            dz = float(dzs[min(idx, len(dzs) - 1)])
            b_mesh = create_box(c, dx, dy, dz, centered=centered)
            all_faces.extend(b_mesh.faces)
            all_edges.extend(b_mesh.edges)

        self.set_output("Mesh", MeshData(faces=all_faces, edges=all_edges, name="Box"))


@register_node
class CylinderNode(NodeBase):
    name = "Cylinder (Solid)"
    category = "Solids"
    description = "Parametric solid cylinder with top/bottom caps."
    header_color = "#b48ead"

    def setup_ports(self) -> None:
        self.add_input("Base", PortType.POINT, Point3D(0, 0, 0))
        self.add_input("Radius", PortType.NUMBER, 1.0)
        self.add_input("Height", PortType.NUMBER, 3.0)
        self.add_input("Segments", PortType.INTEGER, 24)
        self.add_output("Mesh", PortType.MESH, "Solid Cylinder Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        base_in = self.get_input("Base", Point3D(0, 0, 0))
        r_in = self.get_input("Radius", 1.0)
        h_in = self.get_input("Height", 3.0)
        segs_in = self.get_input("Segments", 24)

        if isinstance(base_in, (list, tuple)):
            bases = [p for p in base_in if isinstance(p, Point3D)]
        elif isinstance(base_in, Point3D):
            bases = [base_in]
        else:
            bases = [Point3D(0, 0, 0)]

        radii = r_in if isinstance(r_in, (list, tuple)) else [r_in]
        heights = h_in if isinstance(h_in, (list, tuple)) else [h_in]
        segments = segs_in if isinstance(segs_in, (list, tuple)) else [segs_in]

        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []

        for idx, base in enumerate(bases):
            r = float(radii[min(idx, len(radii) - 1)])
            h = float(heights[min(idx, len(heights) - 1)])
            segs = max(3, int(segments[min(idx, len(segments) - 1)]))

            c_mesh = create_cylinder(base, r, h, segments=segs)
            all_faces.extend(c_mesh.faces)
            all_edges.extend(c_mesh.edges)

        self.set_output("Mesh", MeshData(faces=all_faces, edges=all_edges, name="Cylinder"))


@register_node
class SphereNode(NodeBase):
    name = "Sphere (Solid)"
    category = "Solids"
    description = "Parametric UV sphere mesh."
    header_color = "#b48ead"

    def setup_ports(self) -> None:
        self.add_input("Center", PortType.POINT, Point3D(0, 0, 0))
        self.add_input("Radius", PortType.NUMBER, 1.5)
        self.add_input("Rings", PortType.INTEGER, 12)
        self.add_input("Segments", PortType.INTEGER, 24)
        self.add_output("Mesh", PortType.MESH, "Solid Sphere Mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        center_in = self.get_input("Center", Point3D(0, 0, 0))
        r_in = self.get_input("Radius", 1.5)
        rings_in = self.get_input("Rings", 12)
        segs_in = self.get_input("Segments", 24)

        if isinstance(center_in, (list, tuple)):
            centers = [p for p in center_in if isinstance(p, Point3D)]
        elif isinstance(center_in, Point3D):
            centers = [center_in]
        else:
            centers = [Point3D(0, 0, 0)]

        radii = r_in if isinstance(r_in, (list, tuple)) else [r_in]
        rings_l = rings_in if isinstance(rings_in, (list, tuple)) else [rings_in]
        segs_l = segs_in if isinstance(segs_in, (list, tuple)) else [segs_in]

        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []

        for idx, c in enumerate(centers):
            r = float(radii[min(idx, len(radii) - 1)])
            rings = int(rings_l[min(idx, len(rings_l) - 1)])
            segs = int(segs_l[min(idx, len(segs_l) - 1)])
            s_mesh = create_sphere(c, r, rings=rings, segments=segs)
            all_faces.extend(s_mesh.faces)
            all_edges.extend(s_mesh.edges)

        self.set_output("Mesh", MeshData(faces=all_faces, edges=all_edges, name="Sphere"))


@register_node
class ExtrudeNode(NodeBase):
    name = "Extrude Profile"
    category = "Solids"
    description = "Extrude a planar polygon curve or points along a height/vector into a 3D solid."
    header_color = "#b48ead"

    def setup_ports(self) -> None:
        self.add_input("Profile", PortType.ANY, description="PolylineData or List[Point3D]")
        self.add_input("Height", PortType.NUMBER, 3.0)
        self.add_input("Direction", PortType.VECTOR, Vector3D(0, 0, 1))
        self.add_output("Mesh", PortType.MESH, "Extruded solid mesh")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        prof = self.get_input("Profile")
        h = float(self.get_input("Height", 3.0))
        v_dir = self.get_input("Direction", Vector3D(0, 0, 1))

        if isinstance(v_dir, Vector3D):
            v = v_dir.normalized() * h
        else:
            v = Vector3D(0, 0, h)

        profiles: List[PolylineData] = []
        if isinstance(prof, PolylineData):
            profiles = [prof]
        elif isinstance(prof, (list, tuple)):
            if prof and isinstance(prof[0], PolylineData):
                profiles = [p for p in prof if isinstance(p, PolylineData)]
            elif prof and isinstance(prof[0], Point3D):
                profiles = [PolylineData(points=[p for p in prof if isinstance(p, Point3D)], closed=True)]
            elif prof and isinstance(prof[0], (list, tuple)):
                for sub in prof:
                    pts = [p for p in sub if isinstance(p, Point3D)]
                    if len(pts) >= 3:
                        profiles.append(PolylineData(points=pts, closed=True))

        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []

        for p in profiles:
            if len(p.points) >= 3:
                m = extrude_profile(p.points, v)
                all_faces.extend(m.faces)
                all_edges.extend(m.edges)

        self.set_output("Mesh", MeshData(faces=all_faces, edges=all_edges, name="Extrusion"))


@register_node
class FaceFromPointsNode(NodeBase):
    name = "Face from Points"
    category = "Solids"
    description = "Create a planar polygonal face from a closed loop of points."
    header_color = "#b48ead"

    def setup_ports(self) -> None:
        self.add_input("Points", PortType.ANY, description="List[Point3D]")
        self.add_output("Mesh", PortType.MESH)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        pts_in = self.get_input("Points")
        pts: List[Point3D] = []
        if isinstance(pts_in, PolylineData):
            pts = pts_in.points
        elif isinstance(pts_in, list):
            pts = [p for p in pts_in if isinstance(p, Point3D)]

        if len(pts) >= 3:
            face = FaceData(vertices=pts)
            self.set_output("Mesh", MeshData(faces=[face]))


@register_node
class MeshFromPointsNode(NodeBase):
    name = "Mesh from Points"
    category = "Solids"
    description = "Create a 3D quad or triangulated mesh surface from a structured grid of points with U and V counts."
    header_color = "#d08770"

    def setup_ports(self) -> None:
        self.add_input("Points", PortType.ANY, description="Grid points (List of Point3D or PolylineData)")
        self.add_input("U", PortType.INTEGER, 10, "Points count along U direction (must be >= 2)")
        self.add_input("V", PortType.INTEGER, 0, "Points count along V direction (0 for auto: total / U)")
        self.add_input("Closed U", PortType.BOOLEAN, False, "Wrap mesh in U direction (tube / cylinder)")
        self.add_input("Closed V", PortType.BOOLEAN, False, "Wrap mesh in V direction (torus)")
        self.add_input("Swap UV", PortType.BOOLEAN, False, "Transpose grid order (row-major vs column-major)")
        self.add_input("Triangulate", PortType.BOOLEAN, False, "Split quads into triangles (guarantees planar faces)")
        self.add_output("Mesh", PortType.MESH, "Generated 3D mesh surface")

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        self.error = None
        pts_raw = self.get_input("Points")
        if not pts_raw:
            self.set_output("Mesh", MeshData())
            return

        # Extract 1D list of Point3D
        pts: List[Point3D] = []
        u_override: Optional[int] = None
        v_override: Optional[int] = None

        if isinstance(pts_raw, PolylineData):
            pts = list(pts_raw.points)
        elif isinstance(pts_raw, (list, tuple)):
            if len(pts_raw) > 0 and isinstance(pts_raw[0], (list, tuple)):
                # 2D list of points: row-by-row
                u_override = len(pts_raw)
                v_override = len(pts_raw[0])
                for row in pts_raw:
                    for p in row:
                        if isinstance(p, Point3D):
                            pts.append(p)
                        elif isinstance(p, (list, tuple)) and len(p) >= 3:
                            pts.append(Point3D(float(p[0]), float(p[1]), float(p[2])))
            else:
                for p in pts_raw:
                    if isinstance(p, Point3D):
                        pts.append(p)
                    elif isinstance(p, (list, tuple)) and len(p) >= 3:
                        pts.append(Point3D(float(p[0]), float(p[1]), float(p[2])))

        total = len(pts)
        if total < 4:
            self.error = f"At least 4 points required to form a mesh surface (got {total})"
            self.set_output("Mesh", MeshData())
            return

        u_count = u_override if u_override is not None else max(2, int(self.get_input("U", 10)))
        v_count = v_override if v_override is not None else int(self.get_input("V", 0))

        if v_count <= 0:
            v_count = max(2, total // u_count)

        if total < u_count * v_count:
            self.error = f"Point count ({total}) is less than U ({u_count}) * V ({v_count}) = {u_count * v_count}"
            self.set_output("Mesh", MeshData())
            return

        closed_u = bool(self.get_input("Closed U", False))
        closed_v = bool(self.get_input("Closed V", False))
        swap_uv = bool(self.get_input("Swap UV", False))
        triangulate = bool(self.get_input("Triangulate", False))

        def get_pt(u_idx: int, v_idx: int) -> Point3D:
            if swap_uv:
                idx = v_idx * u_count + u_idx
            else:
                idx = u_idx * v_count + v_idx
            return pts[idx]

        faces: List[FaceData] = []
        edges: List[EdgeData] = []
        seen_edges = set()

        def add_edge(p_a: Point3D, p_b: Point3D, soft: bool = False) -> None:
            k1 = (round(p_a.x, 4), round(p_a.y, 4), round(p_a.z, 4))
            k2 = (round(p_b.x, 4), round(p_b.y, 4), round(p_b.z, 4))
            ek = (min(k1, k2), max(k1, k2))
            if ek not in seen_edges:
                seen_edges.add(ek)
                edges.append(EdgeData(p_a, p_b, soft=soft))

        u_cells = u_count if closed_u else u_count - 1
        v_cells = v_count if closed_v else v_count - 1

        for u in range(u_cells):
            u_next = (u + 1) % u_count
            for v in range(v_cells):
                v_next = (v + 1) % v_count

                p00 = get_pt(u, v)
                p10 = get_pt(u_next, v)
                p11 = get_pt(u_next, v_next)
                p01 = get_pt(u, v_next)

                if triangulate:
                    faces.append(FaceData(vertices=[p00, p10, p11]))
                    faces.append(FaceData(vertices=[p00, p11, p01]))
                    add_edge(p00, p10)
                    add_edge(p10, p11)
                    add_edge(p11, p00, soft=True)
                    add_edge(p11, p01)
                    add_edge(p01, p00)
                else:
                    faces.append(FaceData(vertices=[p00, p10, p11, p01]))
                    add_edge(p00, p10)
                    add_edge(p10, p11)
                    add_edge(p11, p01)
                    add_edge(p01, p00)

        mesh = MeshData(faces=faces, edges=edges, name="MeshFromPoints")
        self.set_output("Mesh", mesh)


# =====================================================================================
# 6. TRANSFORMS & MERGE
# =====================================================================================

@register_node
class MoveNode(NodeBase):
    name = "Move / Translate"
    category = "Transform"
    description = "Translate geometry by a 3D displacement vector."
    header_color = "#88c0d0"

    def setup_ports(self) -> None:
        self.add_input("Geometry", PortType.ANY)
        self.add_input("Vector", PortType.VECTOR, Vector3D(0, 0, 1))
        self.add_output("Result", PortType.ANY)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        geom = self.get_input("Geometry")
        v = self.get_input("Vector", Vector3D(0, 0, 0))

        if isinstance(geom, MeshData):
            self.set_output("Result", geom.translated(v))
        elif isinstance(geom, Point3D):
            self.set_output("Result", geom.translated(v))
        elif isinstance(geom, PolylineData):
            self.set_output("Result", PolylineData([p.translated(v) for p in geom.points], geom.closed))
        elif isinstance(geom, list):
            res = []
            for item in geom:
                if isinstance(item, (MeshData, Point3D)):
                    res.append(item.translated(v))
                else:
                    res.append(item)
            self.set_output("Result", res)


@register_node
class RotateZNode(NodeBase):
    name = "Rotate (Z Axis)"
    category = "Transform"
    description = "Rotate geometry around Z axis by degrees."
    header_color = "#88c0d0"

    def setup_ports(self) -> None:
        self.add_input("Geometry", PortType.ANY)
        self.add_input("Angle Deg", PortType.NUMBER, 45.0)
        self.add_input("Origin", PortType.POINT, Point3D(0, 0, 0))
        self.add_output("Result", PortType.ANY)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        geom = self.get_input("Geometry")
        deg = float(self.get_input("Angle Deg", 45.0))
        orig = self.get_input("Origin", Point3D(0, 0, 0))

        if isinstance(geom, MeshData):
            self.set_output("Result", geom.rotated_z(deg, orig))
        elif isinstance(geom, Point3D):
            self.set_output("Result", geom.rotated_z(deg, orig))


@register_node
class MergeMeshesNode(NodeBase):
    name = "Merge Meshes"
    category = "Transform"
    description = "Combine multiple meshes into one."
    header_color = "#88c0d0"

    def setup_ports(self) -> None:
        self.add_input("Mesh A", PortType.MESH)
        self.add_input("Mesh B", PortType.MESH)
        self.add_output("Merged", PortType.MESH)

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        a = self.get_input("Mesh A")
        b = self.get_input("Mesh B")

        res = MeshData()
        if isinstance(a, MeshData):
            res = res.merge(a)
        elif isinstance(a, list):
            for item in a:
                if isinstance(item, MeshData):
                    res = res.merge(item)

        if isinstance(b, MeshData):
            res = res.merge(b)
        elif isinstance(b, list):
            for item in b:
                if isinstance(item, MeshData):
                    res = res.merge(item)

        self.set_output("Merged", res)


# =====================================================================================
# 7. INGETRAZO SCENE OUTPUT & BAKE
# =====================================================================================

def _point_to_marker(pt: Point3D, size: float = 0.08) -> MeshData:
    """Generate a clean, visible 3D crosshair and diamond point marker for CAD viewport."""
    s = size
    # 3D Crosshair edges (X, Y, Z axes)
    edges = [
        EdgeData(Point3D(pt.x - s, pt.y, pt.z), Point3D(pt.x + s, pt.y, pt.z)),
        EdgeData(Point3D(pt.x, pt.y - s, pt.z), Point3D(pt.x, pt.y + s, pt.z)),
        EdgeData(Point3D(pt.x, pt.y, pt.z - s), Point3D(pt.x, pt.y, pt.z + s)),
    ]
    # Small diamond face in XY plane for solid surface visibility
    d_s = s * 0.7
    diamond_pts = [
        Point3D(pt.x - d_s, pt.y, pt.z),
        Point3D(pt.x, pt.y - d_s, pt.z),
        Point3D(pt.x + d_s, pt.y, pt.z),
        Point3D(pt.x, pt.y + d_s, pt.z),
    ]
    face = FaceData(vertices=diamond_pts)
    d_edges = [
        EdgeData(diamond_pts[0], diamond_pts[1]),
        EdgeData(diamond_pts[1], diamond_pts[2]),
        EdgeData(diamond_pts[2], diamond_pts[3]),
        EdgeData(diamond_pts[3], diamond_pts[0]),
    ]
    return MeshData(faces=[face], edges=edges + d_edges, name="Point")


def _to_mesh_data(geom: Any) -> Optional[MeshData]:
    if isinstance(geom, MeshData):
        return geom
    elif isinstance(geom, Point3D):
        return _point_to_marker(geom)
    elif isinstance(geom, PolylineData):
        if geom.closed and len(geom.points) >= 3:
            face = FaceData(vertices=geom.points)
            edges = [EdgeData(geom.points[i], geom.points[(i + 1) % len(geom.points)]) for i in range(len(geom.points))]
            return MeshData(faces=[face], edges=edges, name="Profile")
        else:
            edges = [EdgeData(geom.points[i], geom.points[i + 1]) for i in range(len(geom.points) - 1)]
            return MeshData(faces=[], edges=edges, name="Curve")
    elif isinstance(geom, FaceData):
        edges = [EdgeData(geom.vertices[i], geom.vertices[(i + 1) % len(geom.vertices)]) for i in range(len(geom.vertices))]
        return MeshData(faces=[geom], edges=edges, name="Face")
    elif isinstance(geom, EdgeData):
        return MeshData(faces=[], edges=[geom], name="Edge")
    elif isinstance(geom, (list, tuple)):
        all_faces: List[FaceData] = []
        all_edges: List[EdgeData] = []
        name = "ParametricModel"

        # Check if list of points: calculate adaptive marker size from point spacing
        pts = [p for p in geom if isinstance(p, Point3D)]
        if pts and len(pts) == len(geom):
            marker_size = 0.08
            if len(pts) >= 2:
                min_d = 1e9
                for i in range(min(10, len(pts) - 1)):
                    d = pts[i].distance_to(pts[i + 1])
                    if d > 1e-4:
                        min_d = min(min_d, d)
                if min_d < 1e8:
                    marker_size = max(0.01, min(0.08, min_d * 0.18))
            for p in pts:
                m = _point_to_marker(p, size=marker_size)
                all_faces.extend(m.faces)
                all_edges.extend(m.edges)
            return MeshData(faces=all_faces, edges=all_edges, name="Points")

        for sub in geom:
            m = _to_mesh_data(sub)
            if m:
                if m.faces:
                    all_faces.extend(m.faces)
                if m.edges:
                    all_edges.extend(m.edges)
                name = m.name or name
        return MeshData(faces=all_faces, edges=all_edges, name=name)
    return None


@register_node
class IngeTrazoOutputNode(NodeBase):
    name = "IngeTrazo Output"
    category = "Scene"
    description = "Stream geometry directly into the active IngeTrazo 3D scene (Live or Bake)."
    header_color = "#bf616a"

    def setup_ports(self) -> None:
        self.add_input("Geometry", PortType.ANY, description="MeshData, faces, curves, or points")
        self.add_input("Group Name", PortType.STRING, "ParametricModel")
        self.add_input("Layer", PortType.STRING, "Layer 0")
        self.add_input("Material", PortType.STRING, "")
        self.widget_values.setdefault("live_update", True)
        self.last_mesh_data: Optional[MeshData] = None

    def compute(self, context: Optional[Dict[str, Any]] = None) -> None:
        geom = self.get_input("Geometry")
        grp_name = str(self.get_input("Group Name", "ParametricModel"))
        layer_name = str(self.get_input("Layer", "Layer 0"))
        mat_name = str(self.get_input("Material", ""))

        mesh = _to_mesh_data(geom)
        if mesh is None:
            mesh = MeshData()
        mesh.name = grp_name
        if layer_name:
            mesh.layer = layer_name
        if mat_name:
            mesh.material = mat_name

        self.last_mesh_data = mesh

        # If live update is enabled and context provided, stream to viewport
        live = bool(self.widget_values.get("live_update", True))
        if live and context and "app" in context:
            self.bake(context["app"], is_live=True)

    def bake(self, app: Any, is_live: bool = False) -> None:
        """Inject geometry into the IngeTrazo document."""
        if not self.last_mesh_data or (not self.last_mesh_data.faces and not self.last_mesh_data.edges):
            return

        try:
            from PySide6.QtGui import QVector3D
            from core.mesh import Mesh
            from core.group import Group
            from core.history import SnapshotImport

            viewport = getattr(app, "viewport", None)
            if not viewport:
                return
            scene = getattr(viewport, "scene", None)
            if not scene:
                return

            mesh_data = self.last_mesh_data
            grp_name = mesh_data.name or "ParametricModel"
            layer_name = mesh_data.layer or "Layer 0"
            mat_name = mesh_data.material

            def mutate(sc):
                # 1. Build native IngeTrazo Mesh
                native_mesh = Mesh()
                for face in mesh_data.faces:
                    if len(face.vertices) < 3:
                        continue
                    try:
                        verts = [QVector3D(float(p.x), float(p.y), float(p.z)) for p in face.vertices]
                        holes = (
                            [[QVector3D(float(p.x), float(p.y), float(p.z)) for p in h] for h in face.holes]
                            if face.holes else None
                        )
                        f = native_mesh.add_face(verts, holes)
                        if f is not None and getattr(f, "attrs", None) is not None:
                            if face.color:
                                f.attrs["color"] = list(face.color)
                            if mat_name:
                                f.attrs["mat"] = mat_name
                            if layer_name:
                                f.attrs["layer"] = layer_name
                    except Exception:
                        pass

                # Add explicit edges
                for edge in mesh_data.edges:
                    try:
                        native_mesh.add_edge(
                            QVector3D(float(edge.a.x), float(edge.a.y), float(edge.a.z)),
                            QVector3D(float(edge.b.x), float(edge.b.y), float(edge.b.z))
                        )
                    except Exception:
                        pass

                native_mesh._chunk_dirty = True
                native_mesh._mut_serial += 1

                # 2. Check if our parametric group already exists
                target_group = None
                for g in getattr(sc, "groups", []):
                    ext = getattr(g, "ext", None)
                    if isinstance(ext, dict) and ext.get("node_editor_id") == self.id:
                        target_group = g
                        break

                if target_group is not None:
                    target_group.mesh = native_mesh
                    target_group.name = grp_name
                    if layer_name:
                        target_group.layer = layer_name
                else:
                    g = Group(native_mesh, name=grp_name)
                    g.component = False
                    if layer_name:
                        g.layer = layer_name
                    g.ext = {"node_editor_id": self.id}
                    sc.groups.append(g)

                # 3. Bump scene version so viewport cache invalidates and renders
                sc.version += 1

            if is_live:
                # Live update: direct mutation without bloating undo history
                mutate(scene)
                notify = getattr(viewport, "notify_scene_changed", None)
                if callable(notify):
                    notify()
                viewport.update()
            else:
                # Bake: record through native undo history
                if hasattr(viewport, "history") and hasattr(viewport.history, "execute"):
                    viewport.history.execute(SnapshotImport(mutate))
                else:
                    mutate(scene)
                notify = getattr(viewport, "notify_scene_changed", None)
                if callable(notify):
                    notify()
                viewport.update()
                if hasattr(viewport, "flash_status"):
                    viewport.flash_status(f"Baked '{grp_name}' to IngeTrazo", 3000)

        except Exception as ex:
            import logging
            logging.getLogger("ingetrazo.plugins.node_editor").error(f"Error baking to IngeTrazo: {ex}", exc_info=True)

