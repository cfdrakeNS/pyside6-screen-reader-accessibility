"""
Styled dialogs for the standalone accessible sample.

Demonstrates AccessibleDialog (Insert+T root window) and message box helpers.
"""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QMessageBox

from accessibility_patterns import exec_styled_message_box


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
    QDialog that is a root in the MSAA/UIA tree so JAWS Insert+T reads this title.

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
            QTimer.singleShot(300, self._refire_focus_for_screen_reader)

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
