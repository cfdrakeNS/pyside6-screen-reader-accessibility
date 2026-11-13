"""
Styled dialogs for the standalone accessible sample.

Demonstrates AccessibleDialog (the JAWS/NVDA Insert+T title command) and message box helpers.
"""

import sys

from PySide6.QtCore import Qt, QTimer, qVersion
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from accessibility_patterns import (
    build_accessible_table_style,
    exec_styled_message_box,
    keep_selection_visible_when_inactive,
)


def _focus_refire_delay_ms() -> int:
    """Return the focus-refire delay suited to the running Qt version.

    Qt 6.11 improved MSAA/UIA top-level window and focus registration on
    Windows, so 100 ms is enough there. Older Qt builds need 300 ms.
    """
    try:
        major, minor = (int(x) for x in qVersion().split(".")[:2])
    except Exception:
        return 300
    return 100 if (major, minor) >= (6, 11) else 300


def _set_win32_owner(child_hwnd: int, owner_hwnd: int) -> None:
    """Set Win32 owner without creating a Qt accessibility parent chain."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.SetWindowLongPtrW(child_hwnd, -8, owner_hwnd)
    except Exception:
        pass


class AccessibleDialog(QDialog):
    """
    QDialog that is a root in the MSAA/UIA tree so the JAWS/NVDA command Insert+T reads this title.

    See doc/PySide6_Accessibility_Patterns_and_Implementation_Reference.md section 4.
    """

    def __init__(self, parent=None, title: str = "Dialog"):
        self._owner_widget = parent
        super().__init__(None)
        self.setWindowTitle(title)
        self.setAccessibleName(title)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        if parent is not None:
            _ = self.winId()
            _set_win32_owner(int(self.winId()), int(parent.winId()))

        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

    @property
    def owner_widget(self):
        return self._owner_widget

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_announce_focus_on_show", True):
            QTimer.singleShot(_focus_refire_delay_ms(), self._refire_focus_for_screen_reader)

    def _refire_focus_for_screen_reader(self):
        if not self.isVisible():
            return
        widget = self.focusWidget()
        if widget is not None and widget is not self:
            widget.clearFocus()
            widget.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self.setFocus(Qt.FocusReason.OtherFocusReason)

    def done(self, result):
        super().done(result)


class StyledDialog(AccessibleDialog):
    """Base class for styled accessible feature dialogs."""

    def __init__(self, parent=None, title: str = "Dialog"):
        super().__init__(parent, title=title)
        self.setModal(True)


def exec_shortcuts_dialog(parent, title: str, shortcuts) -> int:
    """F1 help: one-column read-only shortcut table in an AccessibleDialog (section 7).

    ``shortcuts`` is a sequence of ``(key, action)`` pairs. Escape closes the dialog.
    """
    dlg = AccessibleDialog(parent, title=title)
    dlg.setAccessibleName("Keyboard Shortcuts")
    dlg.setModal(True)
    dlg.resize(420, 320)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 20, 20, 20)

    table = QTableWidget(len(shortcuts), 1, dlg)
    table.setAccessibleName("Shortcuts list")
    table.setHorizontalHeaderLabels([""])
    table.setVerticalHeaderLabels([""] * len(shortcuts))
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setTabKeyNavigation(False)
    table.setShowGrid(False)
    table.setMouseTracking(False)
    table.viewport().setMouseTracking(False)
    table.setAttribute(Qt.WidgetAttribute.WA_Hover, False)
    table.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, False)
    table.setStyleSheet(build_accessible_table_style())
    keep_selection_visible_when_inactive(table)

    for row, (key, action) in enumerate(shortcuts):
        item = QTableWidgetItem(f"{action} - {key}")
        item.setData(Qt.ItemDataRole.AccessibleTextRole, f"{action}: {key}")
        table.setItem(row, 0, item)
    if shortcuts:
        table.setCurrentCell(0, 0)

    layout.addWidget(table)
    table.setFocus(Qt.FocusReason.OtherFocusReason)
    return dlg.exec()


def show_styled_message_box(
    parent,
    icon,
    title,
    text,
    buttons=QMessageBox.StandardButton.Ok,
    default_button=QMessageBox.StandardButton.Ok,
    button_accessibility=None,
):
    """Show a styled, accessible message box (section 18)."""
    return exec_styled_message_box(
        parent,
        icon=icon,
        title=title,
        text=text,
        buttons=buttons,
        default_button=default_button,
        button_accessibility=button_accessibility,
    )
