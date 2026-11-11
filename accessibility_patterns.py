"""
Standalone accessibility patterns for PySide6 sample applications.

Self-contained helpers and AccessibilityMixin — no AbCS dependencies.
See doc/PySide6_Accessibility_Patterns_and_Implementation_Reference.md.
"""

from __future__ import annotations

import html as html_module
import re
import time
from collections.abc import Iterable
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QAccessible, QAccessibleEvent, QFontMetricsF, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
    QTextEdit,
    QWidget,
)

_SCREEN_READER_PROCESSES = {
    "jaws.exe": "jaws",
    "jfw.exe": "jaws",
    "nvda.exe": "nvda",
    "narrator.exe": "narrator",
    "orca": "orca",
    "orca-daemon": "orca",
}

_FOCUS_RESTORE_DELAYS_MS = {
    "jaws": 300,
    "nvda": 1500,
    "narrator": 3500,
    "orca": 800,
}

_PLOT_LINE_WIDTH = 73
_LAST_FOCUS_ANNOUNCE: dict[int, tuple[str, float]] = {}
_FOCUS_ANNOUNCE_DEDUP_SECONDS = 0.9
_MIN_STATUS_READ_DELAY_MS = 300


def init_app_accessibility(app) -> None:
    """Activate Qt accessibility at application startup (section 15)."""
    try:
        QAccessible.setActive(True)
        QAccessible.setRootObject(app)
    except Exception:
        pass


def get_active_screen_reader() -> str:
    """Return detected screen reader name or empty string (section 14)."""
    if psutil is None:
        return ""
    for proc in psutil.process_iter(["name"]):
        name = proc.info.get("name")
        if name is None:
            continue
        reader = _SCREEN_READER_PROCESSES.get(name.lower())
        if reader:
            return reader
    return ""


def is_screen_reader_active() -> bool:
    return bool(get_active_screen_reader())


def get_screen_reader_focus_delay_ms() -> int:
    return _FOCUS_RESTORE_DELAYS_MS.get(get_active_screen_reader(), 0)


def is_unmapped_alt_letter(event, allowed_letters: Iterable[str]) -> bool:
    """Return True when event is Alt+letter/number not in allowed_letters (section 3)."""
    if event.type() != QEvent.Type.KeyPress:
        return False
    if event.modifiers() != Qt.KeyboardModifier.AltModifier:
        return False
    key = event.key()
    if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
        return chr(key) not in set(allowed_letters)
    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return True
    return False


def apply_tooltip_accessibility(widget, tooltip: str, description: str | None = None) -> None:
    """Split sighted tooltip from screen reader description (section 17)."""
    widget.setToolTip(tooltip)
    if description and hasattr(widget, "setAccessibleDescription"):
        widget.setAccessibleDescription(description)


def configure_status_bar_accessibility(status_bar: QStatusBar) -> None:
    """Initialize status bar for screen readers (section 1)."""
    try:
        status_bar.setAccessibleName("")
        status_bar.setAccessibleDescription("")
        status_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    except Exception:
        pass


def prepare_status_bar_for_readback(status_bar: QStatusBar, message: str | None = None) -> str:
    try:
        resolved = (message or status_bar.currentMessage() or "").strip()
        status_bar.setAccessibleDescription("")
        status_bar.setAccessibleName(resolved)
        return resolved
    except Exception:
        return (message or "").strip()


def _accessibility_announcements_enabled() -> bool:
    return QAccessible.isActive() or is_screen_reader_active()


def _status_bar_focus_delay_ms() -> int:
    detected = get_screen_reader_focus_delay_ms()
    if _accessibility_announcements_enabled() and detected <= 0:
        return _MIN_STATUS_READ_DELAY_MS
    return detected


def announce_status_message(
    status_bar: QStatusBar,
    message: str,
    *,
    move_focus: bool = False,
    force_focus_announce: bool = False,
    restore_focus: bool = True,
    update_visible: bool = True,
) -> None:
    """Update status bar and optionally announce via focus brief (section 1)."""
    try:
        message = message or ""
        if update_visible and status_bar.currentMessage() != message:
            status_bar.showMessage(message)

        if not (move_focus and _accessibility_announcements_enabled()):
            return

        prepare_status_bar_for_readback(status_bar, message)
        status_key = id(status_bar)
        now = time.monotonic()
        last_message, last_ts = _LAST_FOCUS_ANNOUNCE.get(status_key, ("", 0.0))
        if (
            not force_focus_announce
            and message == last_message
            and (now - last_ts) < _FOCUS_ANNOUNCE_DEDUP_SECONDS
        ):
            return
        _LAST_FOCUS_ANNOUNCE[status_key] = (message, now)

        app = QApplication.instance()
        if not app:
            return
        # Right after a message box closes, the owner may not be active yet, so
        # the app has no focus widget; the window still remembers its own.
        previous_focus = app.focusWidget() or status_bar.window().focusWidget()
        status_bar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        status_bar.setFocus(Qt.FocusReason.OtherFocusReason)
        QApplication.processEvents()
        if app.focusWidget() != status_bar:
            event = QAccessibleEvent(status_bar, QAccessible.Event.NameChanged)
            QAccessible.updateAccessibility(event)

        def restore_focus_handler() -> None:
            try:
                if restore_focus and previous_focus and app.focusWidget() == status_bar:
                    try:
                        previous_focus.setFocus()
                    except RuntimeError:
                        pass
            finally:
                try:
                    status_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                except RuntimeError:
                    pass

        delay_ms = _status_bar_focus_delay_ms()
        if delay_ms <= 0:
            restore_focus_handler()
        else:
            QTimer.singleShot(delay_ms, restore_focus_handler)
    except Exception:
        pass


def read_status_bar_message(
    status_bar: QStatusBar,
    fallback: str = "",
    *,
    announce_text: str | None = None,
    restore_focus: bool = True,
) -> None:
    """Alt+/ handler: read current status (section 1)."""
    if not _accessibility_announcements_enabled():
        return
    visible = (status_bar.currentMessage() or "").strip()
    if announce_text is not None:
        text = announce_text.strip() or visible or (fallback or "").strip() or "Ready"
    else:
        text = visible or (fallback or "").strip() or "Ready"
    prepare_status_bar_for_readback(status_bar, text)
    announce_status_message(
        status_bar,
        text,
        move_focus=True,
        force_focus_announce=True,
        restore_focus=restore_focus,
    )


def announce_dialog_opened(dialog: QDialog, title: str = "") -> None:
    """Emit DialogStart accessibility event (section 16)."""
    try:
        if title:
            dialog.setAccessibleName(title)
        if QAccessible.isActive():
            event = QAccessibleEvent(dialog, QAccessible.Event.DialogStart)
            QAccessible.updateAccessibility(event)
    except Exception:
        pass


def announce_dialog_closed(dialog: QDialog) -> None:
    """Emit DialogEnd accessibility event (section 16)."""
    try:
        if QAccessible.isActive():
            event = QAccessibleEvent(dialog, QAccessible.Event.DialogEnd)
            QAccessible.updateAccessibility(event)
    except Exception:
        pass


def _collapse_blank_lines(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n\s*\n+", "\n", normalized)


def configure_accessible_read_only_text(
    widget: QTextEdit,
    *,
    text: str,
    accessible_name: str,
    accessible_description: str,
    transparent_background: bool = True,
) -> QTextEdit:
    """Read-only navigable text for arrow-key line review (section 11)."""
    widget.setReadOnly(True)
    widget.setPlainText(_collapse_blank_lines(text))
    widget.setFrameShape(QFrame.Shape.NoFrame)
    widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    widget.setTabChangesFocus(True)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
    widget.setMouseTracking(False)
    widget.viewport().setMouseTracking(False)
    widget.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, False)
    widget.setAccessibleName(accessible_name)
    widget.setAccessibleDescription(accessible_description)
    if transparent_background:
        widget.setStyleSheet("QTextEdit { background: transparent; border: none; }")
    return widget


def create_accessible_read_only_text(
    parent,
    text: str,
    accessible_name: str,
    accessible_description: str,
    *,
    transparent_background: bool = True,
) -> QTextEdit:
    widget = QTextEdit(parent)
    return configure_accessible_read_only_text(
        widget,
        text=text,
        accessible_name=accessible_name,
        accessible_description=accessible_description,
        transparent_background=transparent_background,
    )


def configure_navigable_text_edit(widget: QTextEdit | QPlainTextEdit) -> QTextEdit | QPlainTextEdit:
    """Enable arrow-key line review on editable or read-only text fields."""
    widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    widget.setTabChangesFocus(True)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
    widget.setMouseTracking(False)
    widget.viewport().setMouseTracking(False)
    widget.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, False)
    return widget


_DIALOG_HTML_STYLESHEET = """
p.body { margin-top: 0.1em; margin-bottom: 0.1em; }
p.heading { font-weight: bold; margin-top: 0.35em; margin-bottom: 0.08em; }
p.item { margin-left: 1.25em; margin-top: 0.06em; margin-bottom: 0.06em; }
"""


def blocks_to_dialog_html(blocks: list[tuple[str, str]]) -> str:
    """Convert ``(kind, text)`` blocks to HTML paragraphs; kind is body, heading, or item."""
    parts: list[str] = []
    for kind, text in blocks:
        cleaned = text.strip()
        if not cleaned:
            continue
        escaped = html_module.escape(cleaned)
        if kind == "heading":
            parts.append(f'<p class="heading"><strong>{escaped}</strong></p>')
        elif kind == "item":
            parts.append(f'<p class="item">{escaped}</p>')
        else:
            parts.append(f'<p class="body">{escaped}</p>')
    return "<html><body>\n" + "\n".join(parts) + "\n</body></html>"


def create_dialog_html_text(
    parent,
    blocks: list[tuple[str, str]],
    accessible_name: str,
    accessible_description: str,
    *,
    transparent_background: bool = True,
) -> QTextEdit:
    """Dialog prose as HTML paragraphs for JAWS/NVDA line-by-line review (section 11).

    Use for About, Info, License, and Setup dialog bodies. Each block is one
    paragraph, so the screen reader reads each heading, body line, and list item
    on its own as the user arrows through the text.
    """
    widget = QTextEdit(parent)
    widget.setReadOnly(True)
    widget.setFrameShape(QFrame.Shape.NoFrame)
    widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    widget.setAccessibleName(accessible_name)
    widget.setAccessibleDescription(accessible_description)
    if transparent_background:
        widget.setStyleSheet("QTextEdit { background: transparent; border: none; }")
    configure_navigable_text_edit(widget)
    widget.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
    widget.document().setDefaultStyleSheet(_DIALOG_HTML_STYLESHEET)
    widget.setHtml(blocks_to_dialog_html(blocks))
    return widget


def fit_dialog_width_to_text(
    dialog: QDialog,
    text_widget: QTextEdit,
    *,
    height: int,
    max_screen_fraction: float = 0.9,
) -> None:
    """Resize dialog so no paragraph in text_widget wraps (section 11).

    JAWS reads each visual line of a wrapped paragraph as you arrow up and
    down, then rereads the whole paragraph, so wrapped lines are heard twice.
    Call after the dialog layout is built.
    """
    doc = text_widget.document()
    widest = 0.0
    block = doc.begin()
    while block.isValid():
        fmt = block.blockFormat()
        line = fmt.leftMargin() + fmt.rightMargin() + fmt.textIndent()
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            font = fragment.charFormat().font().resolve(doc.defaultFont())
            line += QFontMetricsF(font).horizontalAdvance(fragment.text())
            it += 1
        widest = max(widest, line)
        block = block.next()
    text_width = widest + 2 * doc.documentMargin()
    margins = dialog.layout().contentsMargins() if dialog.layout() else None
    chrome = (margins.left() + margins.right()) if margins else 0
    chrome += 2 * text_widget.frameWidth()
    chrome += text_widget.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
    width = int(text_width * 1.05) + chrome + 16
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen is not None:
        width = min(width, int(screen.availableGeometry().width() * max_screen_fraction))
    dialog.resize(max(width, dialog.minimumWidth()), height)


YEAR_PLACEHOLDER = "yyyy"
DEFAULT_MIN_YEAR = 1801


def default_year_range() -> tuple[int, int]:
    """Return (min_year, max_year): 1801 through the current year."""
    return DEFAULT_MIN_YEAR, datetime.now().year


def parse_year_text(text: str, *, min_year: int, max_year: int) -> int | None:
    """Return the year, None when blank, or raise ValueError when invalid."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not raw.isdigit() or len(raw) != 4:
        raise ValueError("incomplete")
    year = int(raw)
    if year < min_year or year > max_year:
        raise ValueError("invalid")
    return year


def year_invalid_message(entered: str, *, min_year: int, max_year: int) -> str:
    shown = (entered or "").strip() or "(blank)"
    return (
        f"Year '{shown}' is not valid. "
        f"Enter a year from {min_year} to {max_year}, or leave blank."
    )


class MaskedYearEdit(QLineEdit):
    """Typed four-digit year for screen reader users. Blank means no year.

    A QSpinBox announces every Up/Down step and can change the value silently;
    a plain text field reads the typed digits back reliably in JAWS and NVDA.
    """

    def __init__(self, parent=None, *, min_year: int, max_year: int):
        super().__init__(parent)
        self._min_year = min_year
        self._max_year = max_year
        self.setPlaceholderText(YEAR_PLACEHOLDER)
        self.setMaxLength(4)
        self.setMaximumWidth(110)
        self.setClearButtonEnabled(False)
        self.setAccessibleDescription(
            f"Type a four digit year from {min_year} to {max_year}, "
            "or leave blank. Invalid values show a message when you save."
        )

    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self._place_cursor_for_typing)

    def _place_cursor_for_typing(self) -> None:
        if not self.hasFocus():
            return
        self.deselect()
        self.setCursorPosition(0)

    def setValue(self, value: int | None) -> None:
        self.setText(f"{int(value):04d}" if value else "")

    def value(self) -> int | None:
        try:
            return self.validated_year()
        except ValueError:
            return None

    def validated_year(self) -> int | None:
        return parse_year_text(self.text(), min_year=self._min_year, max_year=self._max_year)

    def invalid_message(self) -> str:
        return year_invalid_message(
            self.text(), min_year=self._min_year, max_year=self._max_year
        )


def make_year_field(parent=None, *, min_year: int | None = None, max_year: int | None = None):
    """Year field: typed MaskedYearEdit when a screen reader is active, else QSpinBox.

    Both support ``setValue()`` and ``value()``. Check the field with
    ``validate_year_field()`` before saving.
    """
    default_min, default_max = default_year_range()
    min_year = default_min if min_year is None else min_year
    max_year = default_max if max_year is None else max_year
    if is_screen_reader_active():
        return MaskedYearEdit(parent, min_year=min_year, max_year=max_year)
    spin = QSpinBox(parent)
    spin.setRange(min_year, max_year)
    spin.setMaximumWidth(110)
    spin.setAccessibleDescription(
        f"Year from {min_year} to {max_year}. Use Up and Down arrows or type a year."
    )
    return spin


def validate_year_field(field, parent) -> bool:
    """Return True when the year is valid; otherwise beep, warn, and focus the field."""
    if not isinstance(field, MaskedYearEdit):
        return True
    try:
        field.validated_year()
        return True
    except ValueError:
        QApplication.beep()
        exec_styled_message_box(
            parent,
            icon=QMessageBox.Icon.Warning,
            title="Invalid Entry",
            text=field.invalid_message(),
        )
        field.setFocus()
        return False


def _wrap_at_words(text: str, width: int = _PLOT_LINE_WIDTH) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def plot_lines_for_review(text: str) -> list[str]:
    """Split prose into review lines for PlotLineList (section 12)."""
    prose = _collapse_blank_lines(text or "").strip()
    if not prose:
        return []
    lines = [line.strip() for line in prose.split("\n") if line.strip()]
    if len(lines) <= 1:
        return _wrap_at_words(prose)
    rating_line = lines[0] if lines[0].startswith("Rating:") else None
    body = " ".join(lines[1:] if rating_line else lines)
    result: list[str] = []
    if rating_line:
        result.append(rating_line)
    if body:
        result.extend(_wrap_at_words(body))
    return result


class _CompactPlotLineDelegate(QStyledItemDelegate):
    _H_MARGIN = 4

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        widget = opt.widget
        style = widget.style() if widget else QApplication.style()
        opt.text = ""
        style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelItemViewItem, opt, painter, widget)
        painter.setPen(opt.palette.color(QPalette.ColorRole.Text))
        rect = opt.rect.adjusted(self._H_MARGIN, 0, -self._H_MARGIN, 0)
        painter.drawText(
            rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            text,
        )

    def sizeHint(self, option, index):
        del index
        return QSize(0, option.fontMetrics.height())


class PlotLineList(QListWidget):
    """One plot line per row for reliable JAWS/NVDA Up/Down review (section 12)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setTabKeyNavigation(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSpacing(0)
        self.setUniformItemSizes(True)
        self.setItemDelegate(_CompactPlotLineDelegate(self))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(False)
        self.viewport().setMouseTracking(False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, False)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, False)
        self.setAccessibleDescription("")
        self.setStyleSheet(
            "QListWidget { border: 1px solid palette(mid); background: palette(base);"
            " outline: none; show-decoration-selected: 0; }"
            "QListWidget::item { padding: 0px; margin: 0px; border: none;"
            " background: palette(base); color: palette(text); }"
            "QListWidget::item:selected, QListWidget::item:focus {"
            " background: palette(base); color: palette(text); border: none; outline: none; }"
        )

    def set_plot_text(self, text: str) -> None:
        self.clear()
        for line in plot_lines_for_review(text):
            item = QListWidgetItem(line)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, line)
            self.addItem(item)
        if self.count():
            self.setCurrentRow(0)


def build_accessible_table_style() -> str:
    """Solid highlight on the selected cell; no hover or focus-rectangle noise (section 9)."""
    return (
        "QTableWidget, QTableView { outline: 0; }"
        "QTableWidget::item:selected, QTableView::item:selected {"
        " background-color: palette(highlight); color: palette(highlighted-text);"
        " border: none; outline: none; }"
        "QTableWidget::item:hover, QTableView::item:hover {"
        " background-color: palette(base); color: palette(text); }"
        "QTableWidget::item:selected:hover, QTableView::item:selected:hover {"
        " background-color: palette(highlight); color: palette(highlighted-text); }"
    )


def keep_selection_visible_when_inactive(widget: QWidget) -> None:
    """Use the active highlight colors when the view loses focus.

    Qt's default inactive selection is pale and hard to see at low vision.
    """
    palette = widget.palette()
    for role in (QPalette.ColorRole.Highlight, QPalette.ColorRole.HighlightedText):
        palette.setColor(
            QPalette.ColorGroup.Inactive,
            role,
            palette.color(QPalette.ColorGroup.Active, role),
        )
    widget.setPalette(palette)


def configure_table(table: QTableWidget) -> None:
    """Hide row headers, reduce hover noise, and make selection easy to see (section 9)."""
    table.verticalHeader().setVisible(False)
    row_count = table.rowCount()
    if row_count:
        table.setVerticalHeaderLabels([""] * row_count)
    table.setMouseTracking(False)
    table.viewport().setMouseTracking(False)
    table.setAttribute(Qt.WidgetAttribute.WA_Hover, False)
    table.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, False)
    table.setStyleSheet(build_accessible_table_style())
    keep_selection_visible_when_inactive(table)


def make_accessible_table_key_press(table: QTableWidget, parent: QWidget):
    """Return a keyPressEvent handler where Tab exits the table (section 22)."""

    def handler(event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            return
        if event.key() == Qt.Key.Key_Tab and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            parent.focusNextChild()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Backtab:
            parent.focusPreviousChild()
            event.accept()
            return
        QTableWidget.keyPressEvent(table, event)

    return handler


def announce_selection(
    status_bar: QStatusBar,
    label: str,
    *,
    count: int = 1,
    hint: str = "",
    announce: bool = True,
) -> None:
    """Announce table/list selection to status bar (section 21)."""
    if count == 1:
        message = f"{label} - selected"
    else:
        message = f"{label} - {count} selected"
    if hint:
        message = f"{message}. {hint}"
    if announce:
        announce_status_message(status_bar, message, move_focus=True, update_visible=True)
    else:
        status_bar.showMessage(message)


def exec_styled_message_box(
    parent,
    *,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    buttons=QMessageBox.StandardButton.Ok,
    default_button=None,
    button_accessibility: dict | None = None,
) -> int:
    """Accessible styled message box (section 18)."""
    from styled_dialogs import AccessibleDialog, _set_win32_owner

    owner = parent.window() if parent is not None else None
    # A modal box disables the window behind it, and JAWS then reads an
    # AccessibleDialog as "<title> unavailable" before the box. Owning the box
    # natively (no Qt parent, window modal) keeps the dialog enabled.
    keep_owner_enabled = isinstance(owner, AccessibleDialog) and owner.isVisible()
    msg = QMessageBox(None if keep_owner_enabled else parent)
    msg.setIcon(icon)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStandardButtons(buttons)
    if default_button is not None:
        msg.setDefaultButton(default_button)
    msg.setAccessibleName(title)
    msg.setAccessibleDescription(text)
    msg.setModal(True)
    if button_accessibility:
        for role, (name, desc) in button_accessibility.items():
            button = msg.button(role)
            if button is not None:
                button.setAccessibleName(name)
                if desc:
                    button.setAccessibleDescription(desc)
    if keep_owner_enabled:
        msg.setWindowModality(Qt.WindowModality.WindowModal)
        _set_win32_owner(int(msg.winId()), int(owner.winId()))
        msg.adjustSize()
        frame = msg.frameGeometry()
        frame.moveCenter(owner.frameGeometry().center())
        msg.move(frame.topLeft())
    result = msg.exec()
    if keep_owner_enabled and owner.isVisible():
        # Without a Qt parent, Qt does not reactivate the owner when the box
        # closes; the caller's setFocus() would land in an inactive window.
        owner.raise_()
        owner.activateWindow()
    return result


def _combo_box_for_event_source(source) -> QComboBox | None:
    """Return the QComboBox when source is the combo or its editable line edit."""
    if isinstance(source, QComboBox):
        return source
    if isinstance(source, QLineEdit):
        parent = source.parentWidget()
        if isinstance(parent, QComboBox) and parent.lineEdit() is source:
            return parent
    return None


def _should_block_combo_arrow_key(event, source) -> bool:
    """True when plain Up/Down should be blocked on an editable combo (section 2)."""
    if event.type() != QEvent.Type.KeyPress:
        return False
    if _combo_box_for_event_source(source) is None:
        return False
    key = event.key()
    if key not in (Qt.Key.Key_Up, Qt.Key.Key_Down):
        return False
    return not (event.modifiers() & Qt.KeyboardModifier.AltModifier)


class AccessibilityMixin:
    """
    Mixin providing core accessibility behavior for sample windows.

    Subclasses should call init_accessibility() after creating a status bar.
    """

    ALLOWED_ALT_KEYS: tuple[str, ...] = ("T", "C", "Y", "I", "L", "S", "D")

    def init_accessibility(self) -> None:
        """Wire status bar, event filters, and screen reader detection."""
        self._default_status = "Ready"
        self._screen_reader = get_active_screen_reader()
        if hasattr(self, "status_bar"):
            configure_status_bar_accessibility(self.status_bar)

        for widget in self.findChildren(QLineEdit):
            widget.installEventFilter(self)
        for widget in self.findChildren(QComboBox):
            widget.installEventFilter(self)
            if widget.lineEdit():
                widget.lineEdit().installEventFilter(self)
        for widget in self.findChildren(QSpinBox):
            widget.installEventFilter(self)

    def detect_screen_reader(self) -> str:
        """Refresh and return detected screen reader name."""
        self._screen_reader = get_active_screen_reader()
        return self._screen_reader

    def set_status(self, message: str, announce: bool = False) -> None:
        """Update the status bar; announce only while the window is visible.

        A focus pulse from a hidden window lands on the window behind it, and
        the screen reader reads that window's title instead of the message.
        """
        if not hasattr(self, "status_bar"):
            return
        self._default_status = message
        announce_status_message(
            self.status_bar,
            message,
            move_focus=announce and self.isVisible(),
            update_visible=True,
        )

    def read_status(self) -> None:
        if hasattr(self, "status_bar"):
            read_status_bar_message(
                self.status_bar,
                fallback=getattr(self, "_default_status", "Ready"),
            )

    def announce_dialog_opened(self, title: str = "") -> None:
        announce_dialog_opened(self, title or self.windowTitle())

    def announce_dialog_closed(self) -> None:
        announce_dialog_closed(self)

    def focus_deselect(self, source) -> None:
        """Defer deselect on FocusIn for editable fields (section 8)."""
        if isinstance(source, QLineEdit):
            QTimer.singleShot(0, lambda w=source: w.deselect())
        elif isinstance(source, QComboBox) and source.lineEdit():
            QTimer.singleShot(0, lambda w=source: w.lineEdit().deselect())
        elif isinstance(source, QSpinBox):
            QTimer.singleShot(0, lambda w=source: w.lineEdit().deselect())

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.KeyPress:
            if is_unmapped_alt_letter(event, self.ALLOWED_ALT_KEYS):
                QApplication.beep()
                return True

            if _should_block_combo_arrow_key(event, source):
                QApplication.beep()
                return True

            combo = _combo_box_for_event_source(source)
            if combo is not None and event.type() == QEvent.Type.KeyPress:
                key = event.key()
                modifiers = event.modifiers()
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and (
                    modifiers & Qt.KeyboardModifier.AltModifier
                ):
                    combo.showPopup()
                    return True

        if event.type() == QEvent.Type.FocusIn:
            combo = _combo_box_for_event_source(source)
            if combo is not None and combo.lineEdit() is not None:
                line = combo.lineEdit()
                QTimer.singleShot(0, lambda w=line: w.deselect())
            elif isinstance(source, QLineEdit):
                self.focus_deselect(source)
            elif isinstance(source, QSpinBox):
                self.focus_deselect(source)

        return super().eventFilter(source, event)
