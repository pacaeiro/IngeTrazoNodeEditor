# SPDX-License-Identifier: GPL-3.0-or-later
"""Comprehensive catalog of parametric modeling nodes for IngeTrazo."""
from __future__ import annotations

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


# =====================================================================================
# 3. VECTOR & POINTS
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

