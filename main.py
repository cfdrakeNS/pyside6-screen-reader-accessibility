"""
Standalone Accessible Sample Application
Demonstrates accessibility patterns documented in doc/PySide6_*.md
"""

import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from accessibility_patterns import (
    AccessibilityMixin,
    PlotLineList,
    announce_dialog_closed,
    announce_dialog_opened,
    announce_selection,
    apply_tooltip_accessibility,
    configure_table,
    create_accessible_read_only_text,
    init_app_accessibility,
    make_accessible_table_key_press,
)
from styled_dialogs import AccessibleDialog, exec_shortcuts_dialog, show_styled_message_box

_CONTEXT_HELP = {
    "main": "Main sample window. Use F1 for shortcuts or Shift+F1 for this context help.",
}


class InfoDialog(AccessibleDialog):
    """Demo feature dialog using AccessibleDialog root-window pattern."""

    def __init__(self, parent=None):
        super().__init__(parent, title="Sample Info Dialog")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.body = create_accessible_read_only_text(
            self,
            "This dialog is an accessibility root window.\n"
            "JAWS Insert+T should read Sample Info Dialog, not the parent window.\n"
            "Test message box opens a box over this dialog. "
            "JAWS should not say Sample Info Dialog unavailable before it.\n"
            "Use arrow keys to review this text line by line.",
            "Info text",
            "Sample information. Use arrow keys to read line by line.",
        )
        layout.addWidget(self.body)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.test_button = QPushButton("Test message box")
        self.test_button.setAccessibleName("Test message box button")
        self.test_button.setAccessibleDescription(
            "Show a message box over this dialog to check that the dialog is not read as unavailable"
        )
        self.test_button.clicked.connect(self.on_test_message_box)
        button_layout.addWidget(self.test_button)

        self.close_button = QPushButton("Close")
        self.close_button.setAccessibleName("Close button")
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

    def showEvent(self, event):
        super().showEvent(event)
        announce_dialog_opened(self, self.windowTitle())
        QTimer.singleShot(0, lambda: self.body.setFocus(Qt.FocusReason.TabFocusReason))

    def on_test_message_box(self):
        show_styled_message_box(
            self,
            icon=QMessageBox.Icon.Information,
            title="Message Over Dialog",
            text="This box is owned by Sample Info Dialog, which stays enabled behind it.",
            button_accessibility={
                QMessageBox.StandardButton.Ok: ("OK", "Close this message and return to the dialog"),
            },
        )
        self.test_button.setFocus()


class AccessibleSampleWindow(AccessibilityMixin, AccessibleDialog):
    """Complete accessible window demonstrating documented patterns.

    AccessibilityMixin must precede AccessibleDialog so eventFilter is not
    shadowed by Qt's QObject implementation.
    """

    ALLOWED_ALT_KEYS = ("T", "C", "Y", "I", "L", "S", "D", "O", "P")

    def __init__(self, parent=None, window_title="Accessible Sample"):
        super().__init__(parent, title=window_title)
        self._window_title = window_title
        self.setAccessibleDescription("Demonstration window for PySide6 accessibility patterns")

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Demo tabs")
        layout.addWidget(self.tabs)

        self._build_form_tab()
        self._build_text_tab()

        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        layout.addWidget(self.status_bar)

        self.init_accessibility()
        reader = self.detect_screen_reader()
        if reader:
            self.set_status(f"Ready - {reader} detected")
        else:
            self.set_status("Ready - all accessibility patterns active")

        self.setup_shortcuts()
        self._shown_once = False

    def showEvent(self, event):
        super().showEvent(event)
        if self._shown_once:
            return
        self._shown_once = True
        announce_dialog_opened(self, self._window_title)
        QTimer.singleShot(0, lambda: self.title_edit.setFocus(Qt.FocusReason.OtherFocusReason))

    def _build_form_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        form = QFormLayout()

        title_label = QLabel("&Title:")
        self.title_edit = QLineEdit()
        self.title_edit.setAccessibleName("Title field")
        self.title_edit.setAccessibleDescription("Enter the title here")
        title_label.setBuddy(self.title_edit)
        form.addRow(title_label, self.title_edit)

        category_label = QLabel("&Category:")
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(["Fiction", "Non-Fiction", "Technical"])
        self.category_combo.setAccessibleName("Category field")
        self.category_combo.setAccessibleDescription("Select or type a category")
        category_label.setBuddy(self.category_combo)
        form.addRow(category_label, self.category_combo)

        year_label = QLabel("&Year:")
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2030)
        self.year_spin.setValue(2026)
        self.year_spin.setAccessibleName("Year field")
        year_label.setBuddy(self.year_spin)
        form.addRow(year_label, self.year_spin)

        tab_layout.addLayout(form)

        table_label = QLabel("Items:")
        self.items_table = QTableWidget(3, 2)
        self.items_table.setHorizontalHeaderLabels(["Name", "Value"])
        self.items_table.setItem(0, 0, QTableWidgetItem("Item 1"))
        self.items_table.item(0, 0).setData(Qt.ItemDataRole.AccessibleTextRole, "First item name")
        self.items_table.setItem(0, 1, QTableWidgetItem("100"))
        self.items_table.item(0, 1).setData(
            Qt.ItemDataRole.AccessibleTextRole, "First item value: 100"
        )
        self.items_table.setItem(1, 0, QTableWidgetItem("Item 2"))
        self.items_table.item(1, 0).setData(Qt.ItemDataRole.AccessibleTextRole, "Second item name")
        self.items_table.setItem(1, 1, QTableWidgetItem("200"))
        self.items_table.setAccessibleName("Items table")
        self.items_table.setAccessibleDescription("Table showing item names and values")
        configure_table(self.items_table)
        self.items_table.keyPressEvent = make_accessible_table_key_press(self.items_table, self)
        self.items_table.itemSelectionChanged.connect(self._on_table_selection_changed)

        tab_layout.addWidget(table_label)
        tab_layout.addWidget(self.items_table)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setAccessibleName("Save button")
        apply_tooltip_accessibility(
            self.save_button,
            "Save current data",
            "Save the current title and category",
        )
        self.save_button.clicked.connect(self.on_save)
        button_layout.addWidget(self.save_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setAccessibleName("Delete button")
        apply_tooltip_accessibility(
            self.delete_button,
            "Delete selected row",
            "Delete the selected item from the table",
        )
        self.delete_button.clicked.connect(self.on_delete)
        button_layout.addWidget(self.delete_button)

        self.info_button = QPushButton("Info Dialog")
        self.info_button.setAccessibleName("Info dialog button")
        apply_tooltip_accessibility(
            self.info_button,
            "Open info dialog",
            "Open a sample AccessibleDialog for Insert+T testing",
        )
        self.info_button.clicked.connect(self.on_open_info_dialog)
        button_layout.addWidget(self.info_button)

        button_layout.addStretch()
        tab_layout.addLayout(button_layout)

        self.setTabOrder(self.title_edit, self.category_combo)
        self.setTabOrder(self.category_combo, self.year_spin)
        self.setTabOrder(self.year_spin, self.items_table)
        self.setTabOrder(self.items_table, self.save_button)
        self.setTabOrder(self.save_button, self.delete_button)
        self.setTabOrder(self.delete_button, self.info_button)

        self.tabs.addTab(tab, "Form and Table")

    def _build_text_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        help_text = create_accessible_read_only_text(
            tab,
            "Read-only navigable text pattern.\n"
            "Use arrow keys to move line by line.\n"
            "Press Tab to leave this area.",
            "Pattern help text",
            "Accessibility pattern description. Use arrow keys to read line by line.",
        )
        layout.addWidget(QLabel("Read-only navigable text:"))
        layout.addWidget(help_text)

        layout.addWidget(QLabel("Plot line-by-line review:"))
        self.plot_list = PlotLineList()
        self.plot_list.setAccessibleName("Plot")
        self.plot_list.set_plot_text(
            "Rating: 4.0 (12 ratings)\n"
            "A long plot summary that wraps at word boundaries for screen reader review. "
            "Each line becomes one list row for reliable Up and Down navigation."
        )
        layout.addWidget(self.plot_list)

        self.tabs.addTab(tab, "Text Review")

    def _on_table_selection_changed(self):
        row = self.items_table.currentRow()
        if row < 0:
            return
        name_item = self.items_table.item(row, 0)
        label = name_item.text() if name_item else f"Row {row + 1}"
        announce_selection(
            self.status_bar,
            label,
            count=1,
            hint="Ctrl+S save, Alt+D delete",
            announce=True,
        )

    def on_save(self):
        title = self.title_edit.text().strip()
        if not title:
            show_styled_message_box(
                self,
                icon=QMessageBox.Icon.Warning,
                title="Validation Error",
                text="Please enter a title before saving.",
                button_accessibility={
                    QMessageBox.StandardButton.Ok: ("OK", "Dismiss validation message"),
                },
            )
            self.title_edit.setFocus()
            self.set_status("Save canceled: title is required", announce=True)
            return
        self.set_status("Data saved successfully", announce=True)
        self.title_edit.setFocus()

    def on_delete(self):
        if self.items_table.currentRow() == -1:
            show_styled_message_box(
                self,
                icon=QMessageBox.Icon.Warning,
                title="No Selection",
                text="Select an item in the table to delete.",
            )
            self.set_status("Delete canceled: no item selected", announce=True)
            self.items_table.setFocus()
            return
        row = self.items_table.currentRow()
        self.items_table.removeRow(row)
        self.set_status("Item deleted successfully", announce=True)
        if self.items_table.rowCount() > 0:
            self.items_table.setCurrentCell(0, 0)
        self.items_table.setFocus()

    def on_open_info_dialog(self):
        dlg = InfoDialog(self)
        dlg.exec()
        announce_dialog_closed(dlg)
        self.set_status("Info dialog closed")
        self.info_button.setFocus()

    def setup_shortcuts(self):
        for seq, handler in (
            ("F1", self.on_show_shortcuts),
            ("Escape", self.on_escape),
            ("Alt+/", self.read_status),
            ("Shift+F1", self.on_context_help),
            ("Ctrl+S", self.on_save),
            ("Alt+T", lambda: self.title_edit.setFocus()),
            ("Alt+C", lambda: self.category_combo.setFocus()),
            ("Alt+Y", lambda: self.year_spin.setFocus()),
            ("Alt+I", lambda: self.items_table.setFocus()),
            ("Alt+L", lambda: self.items_table.setFocus()),
            ("Alt+S", lambda: self.save_button.setFocus()),
            ("Alt+D", lambda: self.delete_button.setFocus()),
            ("Alt+O", self.on_open_info_dialog),
            ("Alt+P", lambda: self.plot_list.setFocus()),
        ):
            shortcut = QShortcut(QKeySequence(seq), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)

    def on_context_help(self):
        """Shift+F1 context help stub (section 20)."""
        show_styled_message_box(
            self,
            icon=QMessageBox.Icon.Information,
            title="Context Help",
            text=_CONTEXT_HELP["main"],
        )

    def on_show_shortcuts(self):
        exec_shortcuts_dialog(
            self,
            "Keyboard Shortcuts - Accessible Sample",
            [
                ("F1", "Show this help"),
                ("Shift+F1", "Context help"),
                ("Alt+/", "Read status"),
                ("Ctrl+S", "Save"),
                ("Alt+T", "Title field"),
                ("Alt+C", "Category field"),
                ("Alt+Y", "Year field"),
                ("Alt+I or Alt+L", "Items table"),
                ("Alt+S", "Save button"),
                ("Alt+D", "Delete button"),
                ("Alt+O", "Open info dialog"),
                ("Alt+P", "Plot list"),
                ("Alt+Down", "Open category list"),
                ("Escape", "Close window with confirmation"),
            ],
        )

    def on_escape(self):
        reply = show_styled_message_box(
            self,
            icon=QMessageBox.Icon.Question,
            title="Close Window",
            text="Are you sure you want to close this window?",
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button=QMessageBox.StandardButton.No,
            button_accessibility={
                QMessageBox.StandardButton.Yes: ("Yes", "Close the sample window"),
                QMessageBox.StandardButton.No: ("No", "Keep the sample window open"),
            },
        )
        if reply == QMessageBox.StandardButton.Yes:
            announce_dialog_closed(self)
            super().reject()


def main():
    app = QApplication(sys.argv)
    init_app_accessibility(app)

    window = AccessibleSampleWindow(window_title="Standalone Accessible Sample")
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
