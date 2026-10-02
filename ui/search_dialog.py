# SPDX-License-Identifier: GPL-3.0-or-later
"""Search and quick-add node palette."""
from __future__ import annotations

from typing import Dict, Optional, Tuple
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QLabel
)

from ..nodes_library import NODE_REGISTRY


class NodeSearchDialog(QDialog):
    """Fuzzy search popup to instantiate nodes."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.selected_node_class: Optional[type] = None
        self.setFixedSize(260, 320)
        self.setStyleSheet("""
            QDialog {
                background: #1e222b;
                border: 1px solid #4c566a;
                border-radius: 8px;
            }
            QLineEdit {
                background: #282c34;
                color: #eceff4;
                border: 1px solid #3b4252;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QListWidget {
                background: #1e222b;
                color: #d8dee9;
                border: none;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #3b4252;
                color: #88c0d0;
            }
            QListWidget::item:hover {
                background: #2e3440;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search nodes...")
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.populate_list("")
        self.search_edit.textChanged.connect(self.populate_list)
        self.list_widget.itemDoubleClicked.connect(self.accept_selection)
        self.search_edit.returnPressed.connect(self.accept_current)

    def populate_list(self, query: str) -> None:
        self.list_widget.clear()
        query = query.strip().lower()

        for cls_name, cls in NODE_REGISTRY.items():
            display_name = f"{cls.category} ▸ {cls.name}"
            if not query or query in cls.name.lower() or query in cls.category.lower():
                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, cls)
                self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Down:
            r = min(self.list_widget.count() - 1, self.list_widget.currentRow() + 1)
            self.list_widget.setCurrentRow(r)
        elif event.key() == Qt.Key_Up:
            r = max(0, self.list_widget.currentRow() - 1)
            self.list_widget.setCurrentRow(r)
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def accept_current(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            self.selected_node_class = item.data(Qt.UserRole)
            self.accept()

    def accept_selection(self, item: QListWidgetItem) -> None:
        self.selected_node_class = item.data(Qt.UserRole)
        self.accept()
