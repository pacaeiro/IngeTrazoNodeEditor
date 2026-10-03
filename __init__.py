# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo Node Editor contributors.
"""IngeTrazo Node Editor — Visual Parametric Modeling Extension for IngeTrazo.

Features:
- Dockable directly in IngeTrazo's side panel tray alongside Properties, BIM, Levels.
- One-click 'Pop Out / Float' into a dedicated multi-monitor window.
- Visual node graph with interactive parameter sliders (Grasshopper / Geometry Nodes style).
- Generative 3D parametric solids (Boxes, Cylinders, Spheres, Extrusions, Curves).
- Real-time live viewport synchronization into IngeTrazo 3D scenes.
- Direct baking to native IngeTrazo groups, layers, and materials with full undo/redo history.
- Save and load node graphs (.itgraph).
"""
from __future__ import annotations

import sys
import logging
from typing import Optional, Any
from pathlib import Path

_pkg_dir = str(Path(__file__).resolve().parent)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

try:
    from tools.base import Tool
except ImportError:
    class Tool:
        pass

log = logging.getLogger("ingetrazo.plugins.node_editor")


class NodeEditorTool(Tool):
    """Extensions menu entry to bring the Node Editor dock panel to the front."""
    name = "Node Editor"
    shortcut = "Ctrl+Shift+N"
    description = "Open the visual parametric node editor for generative 3D modeling."
    uses_snap = False

    def on_activate(self, viewport) -> None:
        window = viewport.window()
        dock = getattr(window, "_node_editor_dock", None)
        if dock is not None:
            # Switch to the Node Editor tab in the side tray
            if hasattr(window, "set_tray_shown"):
                window.set_tray_shown(dock, True)
            dock.show()
            dock.raise_()
        else:
            # Fallback if opened before dock registration
            panel = getattr(window, "_node_editor_panel", None)
            if panel is not None:
                panel.show()
                panel.raise_()

    def on_deactivate(self, viewport) -> None:
        pass


def setup(app) -> None:
    """Extension initialization called by IngeTrazo at startup. Registers the dock panel in the side tray."""
    try:
        from .ui.window import NodeEditorWidget

        # 1. Create dock panel widget in the side tray alongside Properties, BIM, Levels
        editor_panel = NodeEditorWidget(app)
        dock = app.add_panel("Node Editor", editor_panel)
        if dock is not None:
            editor_panel.set_dock_widget(dock)

        # Store handles on the main window for quick access
        win = getattr(app, "_window", None)
        if win:
            win._node_editor_dock = dock
            win._node_editor_panel = editor_panel
            win._extension_app_handle = app

        # 2. Add action in Extensions menu
        def show_editor():
            if dock is not None:
                app.show_panel(dock)
                dock.raise_()

        sub = app.add_menu("Node Editor")
        if sub is not None:
            sub.addAction("Open Node Editor… (Ctrl+Shift+N)", show_editor)

        log.info("IngeTrazo Node Editor dock panel registered in side tray successfully.")

    except Exception as ex:
        log.error(f"Error during Node Editor setup: {ex}", exc_info=True)
