"""
Popup Insert+B lab.

Copies of three AbCS main window popups (Duplicate Check, Read date, and
Recently Added), plus variants that each change one thing, to find why the
JAWS/NVDA command Insert+B reads Duplicate Check as a dialog but not the two
date popups. Each popup prints its accessibility tree to the terminal once
it has settled.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QAccessible, QFont, QFontMetrics, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAccessibleWidget,
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStatusBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from accessibility_patterns import (
    MaskedDateEdit,
    configure_classic_date_field,
    configure_status_bar_accessibility,
    is_screen_reader_active,
    make_classic_date_field,
    read_status_bar_message,
    validate_date_field,
)
from styled_dialogs import AccessibleDialog

SAMPLE_BOOK = "The Hobbit"
LOG_DELAY_MS = 1000
DATE_FONT_POINT_SIZE = 14

DUPLICATE_MATCH_OPTIONS = (
    "Title + Author + Year + Collection",
    "Title + Author + Year",
    "Title + Author + Collection",
    "Title + Author",
)


@dataclass(frozen=True)
class PopupVariant:
    """One test popup. ``base`` is the AbCS popup it copies."""

    number: int
    label: str
    base: str
    field: str
    prompt_label: bool = False
    force_focus: bool = True
    dialog_description: bool = False
    icon_and_center: bool = True
    status_bar: bool = True
    label_first: bool = False
    extra_text_field: bool = False
    read_only: bool = False
    open_on_ok: bool = False
    field_focus_delay_ms: int = 0
    native_field: bool = False

    @property
    def heading(self) -> str:
        return f"Popup {self.number}: {self.label}"


POPUP_VARIANTS = (
    PopupVariant(1, "Duplicate Check copy", "duplicate", "combo"),
    PopupVariant(2, "Read date copy, typed date", "read_date", "typed_date"),
    PopupVariant(3, "Read date copy, calendar date", "read_date", "classic_date"),
    PopupVariant(4, "Recently Added copy, typed date", "recently_added", "typed_date"),
    PopupVariant(5, "Read date with a combo box instead of the date", "read_date", "combo"),
    PopupVariant(6, "Read date with a visible prompt", "read_date", "typed_date", prompt_label=True),
    PopupVariant(7, "Read date without forced first focus", "read_date", "typed_date", force_focus=False),
    PopupVariant(8, "Read date with a dialog description", "read_date", "typed_date", dialog_description=True),
    PopupVariant(9, "Read date without icon or centering", "read_date", "typed_date", icon_and_center=False),
    PopupVariant(10, "Duplicate Check with a typed date instead of the combo box", "duplicate", "typed_date"),
    PopupVariant(11, "Recently Added without a status bar", "recently_added", "typed_date", status_bar=False),
    PopupVariant(12, "Recently Added with the label before the field", "recently_added", "typed_date", label_first=True),
    PopupVariant(13, "Duplicate Check with an extra text field, focus on the combo box", "duplicate", "combo", extra_text_field=True),
    PopupVariant(14, "Read date with an editable combo box for the date", "read_date", "editable_combo"),
    PopupVariant(15, "Read date with a read-only date field", "read_date", "typed_date", read_only=True),
    PopupVariant(16, "Read date opening on the OK button", "read_date", "typed_date", open_on_ok=True),
    PopupVariant(
        17,
        "Read date opening on the OK button, then moving to the date",
        "read_date",
        "typed_date",
        open_on_ok=True,
        field_focus_delay_ms=800,
    ),
    PopupVariant(18, "Read date with the date field in its own native window", "read_date", "typed_date", native_field=True),
    PopupVariant(19, "Read date with year, month, and day combo boxes", "read_date", "date_combos"),
)


class _DateCombos(QWidget):
    """Year, month, and day as three non-editable combo boxes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        today = QDate.currentDate()
        self.year = QComboBox(self)
        self.year.setAccessibleName("Year")
        self.year.addItems([str(y) for y in range(today.year(), 1949, -1)])
        self.month = QComboBox(self)
        self.month.setAccessibleName("Month")
        self.month.addItems([f"{m:02d}" for m in range(1, 13)])
        self.day = QComboBox(self)
        self.day.setAccessibleName("Day")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for combo in (self.year, self.month, self.day):
            layout.addWidget(combo)
        self.setFocusProxy(self.year)
        self.year.currentIndexChanged.connect(self._refill_days)
        self.month.currentIndexChanged.connect(self._refill_days)
        self._refill_days()

    def _refill_days(self, *_args) -> None:
        keep = self.day.currentIndex()
        days = QDate(int(self.year.currentText()), self.month.currentIndex() + 1, 1).daysInMonth()
        self.day.blockSignals(True)
        self.day.clear()
        self.day.addItems([f"{d:02d}" for d in range(1, days + 1)])
        self.day.setCurrentIndex(min(max(keep, 0), days - 1))
        self.day.blockSignals(False)

    def setDate(self, qdate: QDate) -> None:
        self.year.setCurrentText(str(qdate.year()))
        self.month.setCurrentIndex(qdate.month() - 1)
        self.day.setCurrentIndex(qdate.day() - 1)

    def text(self) -> str:
        return f"{self.year.currentText()}-{self.month.currentText()}-{self.day.currentText()}"

_date_fields_as_plain_text = False
_plain_text_factory_installed = False


class _PlainTextTypedDate(MaskedDateEdit):
    lab_plain_text = True


class _PlainTextClassicDate(QDateEdit):
    lab_plain_text = True


def _plain_text_factory(_key, obj):
    """Report lab-marked date fields as static text instead of an edit field."""
    if getattr(obj, "lab_plain_text", False):
        return QAccessibleWidget(obj, QAccessible.Role.StaticText)
    return None


def set_date_fields_as_plain_text(enabled: bool) -> None:
    """Make popups opened from now on report their date field as plain text."""
    global _date_fields_as_plain_text, _plain_text_factory_installed
    if enabled and not _plain_text_factory_installed:
        QAccessible.installFactory(_plain_text_factory)
        _plain_text_factory_installed = True
    _date_fields_as_plain_text = enabled


def exec_popup_variant(owner, variant: PopupVariant) -> str:
    """Open the test popup modally and return a status message for the owner."""
    builders = {
        "duplicate": _exec_duplicate_check,
        "read_date": _exec_read_date,
        "recently_added": _exec_recently_added,
    }
    return builders[variant.base](owner, variant)


# ---------------------------------------------------------------------------
# Accessibility tree logging
# ---------------------------------------------------------------------------


def _describe(iface) -> str:
    if iface is None or not iface.isValid():
        return "(no accessible interface)"
    role = iface.role()
    role_name = getattr(role, "name", str(role))
    name = iface.text(QAccessible.Text.Name)
    description = iface.text(QAccessible.Text.Description)
    text = f"{role_name} name={name!r}"
    if description:
        text += f" description={description!r}"
    if getattr(iface.state(), "focused", False):
        text += " [focused]"
    return text


def _walk(iface, depth: int, lines: list[str], max_depth: int = 4) -> None:
    lines.append("  " * depth + _describe(iface))
    if depth >= max_depth or iface is None or not iface.isValid():
        return
    for index in range(iface.childCount()):
        _walk(iface.child(index), depth + 1, lines, max_depth)


def _win32_lines(hwnd: int) -> list[str]:
    if sys.platform != "win32":
        return []
    try:
        user32 = ctypes.WinDLL("user32")
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.GetWindowLongPtrW.argtypes = (ctypes.c_void_p, ctypes.c_int)
        user32.GetWindow.restype = ctypes.c_void_p
        user32.GetWindow.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(ctypes.c_void_p(hwnd), class_name, 256)
        style = user32.GetWindowLongPtrW(hwnd, -16) & 0xFFFFFFFF
        ex_style = user32.GetWindowLongPtrW(hwnd, -20) & 0xFFFFFFFF
        owner = user32.GetWindow(hwnd, 4)
    except Exception as exc:
        return [f"Win32 details unavailable: {exc}"]
    return [
        f"Win32 class: {class_name.value}",
        f"Win32 style: 0x{style:08X}  extended style: 0x{ex_style:08X}",
        f"Win32 owner: {hex(owner) if owner else 'none'}",
    ]


def log_accessible_tree(dlg: QDialog, heading: str) -> None:
    """Print the dialog's Qt accessibility tree and Win32 window details."""
    if not dlg.isVisible():
        return
    iface = QAccessible.queryAccessibleInterface(dlg)
    parent = iface.parent() if iface is not None and iface.isValid() else None
    focus = QApplication.focusWidget()
    lines = [
        f"=== {heading} ===",
        f"Window title: {dlg.windowTitle()!r}",
        f"Active window is this popup: {QApplication.activeWindow() is dlg}",
        f"Date fields reported as plain text: {'yes' if _date_fields_as_plain_text else 'no'}",
        *_win32_lines(int(dlg.winId())),
        f"Accessible parent: {_describe(parent)}",
        "Focus: " + (_describe(QAccessible.queryAccessibleInterface(focus)) if focus else "none"),
        "Focus has its own native window: "
        + ("yes" if focus is not None and focus is not dlg and focus.internalWinId() else "no"),
        "Tree:",
    ]
    _walk(iface, 1, lines)
    print("\n".join(lines) + "\n", flush=True)


def _exec_and_delete(dlg: QDialog, variant: PopupVariant, accepted_message) -> str:
    """Run the popup modally, log its tree once settled, and return a status message.

    The popup has no Qt parent, so Python callbacks keep it alive; without
    deleteLater() it is destroyed after QApplication at exit and crashes.
    """
    QTimer.singleShot(LOG_DELAY_MS, dlg, lambda: log_accessible_tree(dlg, variant.heading))
    accepted = dlg.exec() == QDialog.DialogCode.Accepted
    message = accepted_message() if accepted else f"Popup {variant.number} canceled"
    dlg.deleteLater()
    return message


# ---------------------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------------------


def _make_field(kind: str, parent, *, allow_blank: bool):
    if kind == "typed_date":
        typed_class = _PlainTextTypedDate if _date_fields_as_plain_text else MaskedDateEdit
        return typed_class(parent, allow_blank=allow_blank, disallow_future=True)
    if kind == "classic_date":
        if _date_fields_as_plain_text:
            return configure_classic_date_field(_PlainTextClassicDate(parent))
        return make_classic_date_field(parent)
    if kind == "date_combos":
        return _DateCombos(parent)
    combo = QComboBox(parent)
    combo.setEditable(kind == "editable_combo")
    today = QDate.currentDate()
    for days_back in (0, 1, 7, 30):
        combo.addItem(today.addDays(-days_back).toString("yyyy-MM-dd"))
    return combo


def _set_field_date(field, qdate: QDate) -> None:
    if hasattr(field, "setDate"):
        field.setDate(qdate)


def _field_value(field) -> str:
    if isinstance(field, QComboBox):
        return field.currentText()
    if isinstance(field, (MaskedDateEdit, _DateCombos)):
        return field.text().strip()
    return field.date().toString("yyyy-MM-dd")


def _set_large_font(field) -> None:
    font = QFont(field.font())
    font.setPointSize(DATE_FONT_POINT_SIZE)
    field.setFont(font)


def _size_to_title(dlg: QDialog, min_height: int = 0) -> None:
    title_width = QFontMetrics(dlg.font()).horizontalAdvance(dlg.windowTitle()) + 80
    width = max(title_width, dlg.sizeHint().width() + 120, 400)
    dlg.resize(width, max(dlg.sizeHint().height(), min_height))


def _center_on_screen(dlg: QDialog) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    geometry = dlg.frameGeometry()
    geometry.moveCenter(screen.availableGeometry().center())
    dlg.move(geometry.topLeft())


def _apply_window_icon(dlg: QDialog) -> None:
    dlg.setWindowIcon(
        QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView)
    )


class _DateDialog(AccessibleDialog):
    """AbCS ReadDateDialog / RecentlyAddedDialog: forced first focus, Enter accepts."""

    def __init__(self, parent, *, force_focus: bool, buttons_take_enter: bool):
        super().__init__(parent)
        self.date_field = None
        self.first_focus_widget = None
        self.field_focus_delay_ms = 0
        self._force_focus = force_focus
        self._buttons_take_enter = buttons_take_enter

    def showEvent(self, event):
        super().showEvent(event)
        if self._force_focus:
            QTimer.singleShot(0, self._focus_first_control)

    def _focus_first_control(self):
        if self.first_focus_widget is None:
            self._focus_date_field()
            return
        if not self.isVisible():
            return
        self.first_focus_widget.setFocus(Qt.FocusReason.OtherFocusReason)
        if self.field_focus_delay_ms:
            QTimer.singleShot(self.field_focus_delay_ms, self._focus_date_field)

    def _focus_date_field(self):
        if self.date_field is None or not self.isVisible():
            return
        self.date_field.setFocus(Qt.FocusReason.OtherFocusReason)
        if isinstance(self.date_field, MaskedDateEdit):
            self.date_field.selectAll()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            focused = self.focusWidget()
            if self._buttons_take_enter and isinstance(focused, QPushButton):
                focused.click()
                event.accept()
                return
            if self.date_field is not None:
                self.date_field.setFocus()
            QTimer.singleShot(0, self.accept)
            event.accept()
            return
        super().keyPressEvent(event)

    def accept(self):
        if self.date_field is not None and not validate_date_field(self.date_field, self):
            return
        super().accept()


# ---------------------------------------------------------------------------
# Duplicate Check (AbCS MainWindow.on_duplicate_check)
# ---------------------------------------------------------------------------


def _exec_duplicate_check(owner, variant: PopupVariant) -> str:
    dialog = AccessibleDialog(owner, title="Duplicate Check")
    dialog.setAccessibleName("")
    dialog.setAccessibleDescription(
        "Select duplicate match mode and start duplicate checking. Press Escape to close."
    )

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)
    layout.addWidget(QLabel("Select duplicate match type:"))
    layout.addWidget(QLabel("Press Escape to close."))

    if variant.field == "combo":
        field = QComboBox()
        field.setAccessibleName("Duplicate match type")
        field.setAccessibleDescription("Same duplicate matching options as Preferences")
        field.addItems(DUPLICATE_MATCH_OPTIONS)
    else:
        field = _make_field(variant.field, dialog, allow_blank=False)
        _set_field_date(field, QDate.currentDate())
    layout.addWidget(field)

    if variant.extra_text_field:
        notes = QLineEdit()
        notes.setAccessibleName("Notes")
        notes.setAccessibleDescription("Optional notes. Not used by the duplicate check.")
        layout.addWidget(notes)

    buttons_layout = QHBoxLayout()
    start_button = QPushButton("Start")
    start_button.setAccessibleName("Start duplicate check")
    start_button.setAccessibleDescription("Start duplicate check")
    start_button.clicked.connect(dialog.accept)

    escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), dialog)
    escape_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
    escape_shortcut.activated.connect(dialog.reject)

    def focus_field():
        field.setFocus()
        if isinstance(field, QComboBox):
            field.showPopup()

    for key, handler in (("Alt+R", start_button.click), ("Alt+M", focus_field)):
        shortcut = QShortcut(QKeySequence(key), dialog)
        shortcut.activated.connect(handler)

    buttons_layout.addStretch()
    buttons_layout.addWidget(start_button)
    layout.addLayout(buttons_layout)

    return _exec_and_delete(
        dialog, variant, lambda: f"Popup {variant.number} started with {_field_value(field)}"
    )


# ---------------------------------------------------------------------------
# Read date (AbCS MainWindow.show_read_date_dialog)
# ---------------------------------------------------------------------------


def _exec_read_date(owner, variant: PopupVariant) -> str:
    dlg = _DateDialog(owner, force_focus=variant.force_focus, buttons_take_enter=True)
    dlg.setWindowTitle(f"Set Read Date for '{SAMPLE_BOOK}'")
    dlg.setAccessibleName("")
    if variant.dialog_description:
        dlg.setAccessibleDescription(f"Set the date you finished '{SAMPLE_BOOK}'.")
    if variant.icon_and_center:
        _apply_window_icon(dlg)
    layout = QVBoxLayout(dlg)

    if variant.field == "typed_date":
        prompt_text = f"Type the date you finished '{SAMPLE_BOOK}' as year-month-day."
    elif variant.field == "date_combos":
        prompt_text = ""
    elif variant.field == "editable_combo":
        prompt_text = (
            f"Type the date you finished '{SAMPLE_BOOK}' as year-month-day, "
            "or press Alt+Down to choose a recent date."
        )
    else:
        prompt_text = f"Choose the date you finished '{SAMPLE_BOOK}'."
        if variant.field == "classic_date":
            prompt_text += " Alt+Down opens the calendar."

    # Accessible child order follows creation order, so the prompt is created
    # first to come before the field, as the labels do in Duplicate Check.
    if variant.prompt_label:
        layout.addWidget(QLabel(prompt_text, dlg))

    field = _make_field(variant.field, dlg, allow_blank=True)
    field.setAccessibleName("Date read")
    _set_field_date(field, QDate.currentDate())
    _set_large_font(field)
    if variant.read_only:
        field.setReadOnly(True)
    if variant.native_field:
        field.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
    if prompt_text:
        field.setAccessibleDescription(f"{prompt_text} OK saves the date. Clear removes it.")
    layout.addWidget(field)

    date_row = QHBoxLayout()
    date_row.addStretch(1)

    clear_btn = QPushButton("Clear")
    clear_btn.setAccessibleName("Clear")
    clear_btn.setAccessibleDescription("Clear the read date for this book")
    clear_btn.setAutoDefault(False)
    clear_btn.setDefault(False)
    clear_btn.clicked.connect(lambda: dlg.done(QDialog.DialogCode.Rejected))

    ok_btn = QPushButton("OK")
    ok_btn.setAccessibleName("OK")
    ok_btn.setAccessibleDescription("Save the date and close. No extra confirmation.")
    ok_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    ok_btn.setDefault(True)
    ok_btn.setAutoDefault(True)
    clear_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    ok_btn.clicked.connect(dlg.accept)

    date_row.addWidget(ok_btn)
    date_row.addWidget(clear_btn)
    layout.addLayout(date_row)
    dlg.date_field = field
    if variant.open_on_ok:
        dlg.first_focus_widget = ok_btn
        dlg.field_focus_delay_ms = variant.field_focus_delay_ms
        # Otherwise Qt gives the date field (first in Tab order) focus as the window opens.
        ok_btn.setFocus(Qt.FocusReason.OtherFocusReason)

    _size_to_title(dlg)
    if variant.icon_and_center:
        _center_on_screen(dlg)

    return _exec_and_delete(
        dlg,
        variant,
        lambda: f"Popup {variant.number} saved read date {_field_value(field) or '(blank)'}",
    )


# ---------------------------------------------------------------------------
# Recently Added (AbCS MainWindow.on_recently_added)
# ---------------------------------------------------------------------------


def _exec_recently_added(owner, variant: PopupVariant) -> str:
    dlg = _DateDialog(owner, force_focus=variant.force_focus, buttons_take_enter=False)
    dlg.setWindowTitle("Recently Added")
    dlg.setAccessibleName("Recently Added")
    dlg.setAccessibleDescription("Show books added on or after the selected date.")
    if variant.icon_and_center:
        _apply_window_icon(dlg)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)

    date_row = QHBoxLayout()
    date_label = QLabel("&Added since:", dlg if variant.label_first else None)
    field = _make_field(variant.field, dlg, allow_blank=False)
    field.setAccessibleName("Added since date")
    _set_field_date(field, QDate.currentDate().addMonths(-2))
    typing_note = (
        "Type the date as year-month-day. "
        if variant.field == "typed_date"
        else "Alt+Down opens the calendar. "
    )
    field.setAccessibleDescription(
        "Books added on or after this date are shown. " + typing_note + "Press Enter to filter."
    )
    _set_large_font(field)
    date_label.setBuddy(field)
    date_row.addWidget(date_label)
    date_row.addWidget(field, 1)
    layout.addLayout(date_row)

    if variant.status_bar:
        dialog_status = QStatusBar(dlg)
        dialog_status.setSizeGripEnabled(False)
        configure_status_bar_accessibility(dialog_status)
        dialog_status.showMessage(
            "Choose a date and press Enter to filter."
            + (" Alt+/ read status" if is_screen_reader_active() else "")
        )
        layout.addWidget(dialog_status)

        status_shortcut = QShortcut(QKeySequence("Alt+/"), dlg)
        status_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        status_shortcut.activated.connect(
            lambda: read_status_bar_message(dialog_status, fallback="Recently added dialog ready")
        )

    dlg.date_field = field

    _size_to_title(dlg, min_height=120)
    if variant.icon_and_center:
        _center_on_screen(dlg)

    return _exec_and_delete(
        dlg, variant, lambda: f"Popup {variant.number} filtered from {_field_value(field)}"
    )
