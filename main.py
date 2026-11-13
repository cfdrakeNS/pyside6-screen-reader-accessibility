"""
Standalone Accessible Sample Application
Demonstrates accessibility patterns documented in doc/PySide6_*.md
"""

import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
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
    select_first_cell_when_focused,
    create_dialog_html_text,
    fit_dialog_width_to_text,
    init_app_accessibility,
    make_accessible_table_key_press,
    make_year_field,
    set_accessible_table_rows,
    validate_year_field,
)
from popup_lab import POPUP_VARIANTS, exec_popup_variant, set_date_fields_as_plain_text
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
        self.body = create_dialog_html_text(
            self,
            [
                ("body", "Sample Info Dialog - accessibility patterns demo"),
                ("body", "This dialog is an accessibility root window."),
                ("heading", "WHAT TO CHECK"),
                ("item", "The JAWS/NVDA command Insert+T reads the window title: Sample Info Dialog."),
                ("item", "It should not read the title of the window behind it."),
                ("item", "Up and Down arrows read this text one line at a time."),
                ("item", "Test message box opens a box over this dialog."),
                ("item", "JAWS/NVDA should not say Sample Info Dialog unavailable first."),
                ("item", "In the message box, the JAWS/NVDA command Insert+B reads the dialog."),
                ("item", "Tab moves to the Test message box and Close buttons."),
                ("heading", "HOW THIS TEXT IS BUILT"),
                ("body", "Each heading, line, and list item is its own paragraph."),
                ("body", "The dialog is sized so no paragraph wraps."),
                ("body", "JAWS/NVDA rereads a wrapped line as you arrow up and down."),
            ],
            "Info text",
            "Sample information. Use arrow keys to read line by line. "
            "Press Tab to move to the buttons.",
        )
        layout.addWidget(self.body, stretch=1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.test_button = QPushButton("Test message box")
        self.test_button.setAccessibleName("Test message box")
        self.test_button.setAccessibleDescription(
            "Show a message box over this dialog to check that the dialog is not read as unavailable"
        )
        self.test_button.clicked.connect(self.on_test_message_box)
        button_layout.addWidget(self.test_button)

        self.close_button = QPushButton("Close")
        self.close_button.setAccessibleName("Close")
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)
        fit_dialog_width_to_text(self, self.body, height=420)

    def showEvent(self, event):
        super().showEvent(event)
        announce_dialog_opened(self, self.windowTitle())
        QTimer.singleShot(0, lambda: self.body.setFocus(Qt.FocusReason.TabFocusReason))

    def on_test_message_box(self):
        show_styled_message_box(
            self,
            icon=QMessageBox.Icon.Information,
            title="Message Over Dialog",
            text=(
                "This box is owned by Sample Info Dialog, which stays enabled behind it.\n"
                "Press the JAWS/NVDA command Insert+B to read this dialog again."
            ),
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

    ALLOWED_ALT_KEYS = ("T", "C", "Y", "L", "D", "I", "P", "U")

    def __init__(self, parent=None, window_title="Accessible Sample"):
        super().__init__(parent, title=window_title)
        self._window_title = window_title
        self.setAccessibleDescription("Demonstration window for PySide6 accessibility patterns")

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.setAccessibleName("Demo sections")
        layout.addWidget(self.tabs)

        self._build_form_tab()
        self._build_text_tab()
        self._build_popup_tests_tab()

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
        self.title_edit.setAccessibleName("Title")
        self.title_edit.setAccessibleDescription("Enter the title here")
        title_label.setBuddy(self.title_edit)
        form.addRow(title_label, self.title_edit)

        category_label = QLabel("&Category:")
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(["Fiction", "Non-Fiction", "Technical"])
        self.category_combo.setAccessibleName("Category")
        self.category_combo.setAccessibleDescription("Select or type a category")
        category_label.setBuddy(self.category_combo)
        form.addRow(category_label, self.category_combo)

        year_label = QLabel("&Year:")
        self.year_field = make_year_field(self)
        self.year_field.setValue(datetime.now().year)
        self.year_field.setAccessibleName("Year")
        year_label.setBuddy(self.year_field)
        form.addRow(year_label, self.year_field)

        tab_layout.addLayout(form)

        table_label = QLabel("Items:")
        self.items_table = QTableWidget(0, 2)
        self.items_table.setHorizontalHeaderLabels(["Name", "Value"])
        set_accessible_table_rows(
            self.items_table,
            [("Item 1", "100"), ("Item 2", "200"), ("Item 3", "300")],
        )
        self.items_table.setAccessibleName("Items")
        self.items_table.setAccessibleDescription(
            "Table showing item names and values. Each row reads the name and value together."
        )
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setTabKeyNavigation(False)
        configure_table(self.items_table)
        select_first_cell_when_focused(self.items_table)
        self.items_table.keyPressEvent = make_accessible_table_key_press(self.items_table, self)
        self.items_table.itemSelectionChanged.connect(self._on_table_selection_changed)

        tab_layout.addWidget(table_label)
        tab_layout.addWidget(self.items_table)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setAccessibleName("Save")
        apply_tooltip_accessibility(
            self.save_button,
            "Save current data",
            "Save the current title and category - Ctrl+S",
        )
        self.save_button.clicked.connect(self.on_save)
        button_layout.addWidget(self.save_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setAccessibleName("Delete")
        apply_tooltip_accessibility(
            self.delete_button,
            "Delete selected row",
            "Delete the selected item from the table - Alt+D",
        )
        self.delete_button.clicked.connect(self.on_delete)
        button_layout.addWidget(self.delete_button)

        self.info_button = QPushButton("Info Dialog")
        self.info_button.setAccessibleName("Info dialog")
        apply_tooltip_accessibility(
            self.info_button,
            "Open info dialog",
            "Open a sample dialog - Alt+I. The JAWS/NVDA command Insert+T reads the title",
        )
        self.info_button.clicked.connect(self.on_open_info_dialog)
        button_layout.addWidget(self.info_button)

        button_layout.addStretch()
        tab_layout.addLayout(button_layout)

        # A form with several buttons: no default button; Enter clicks the
        # focused button (keyPressEvent), so Enter in a field fires nothing.
        for button in (self.save_button, self.delete_button, self.info_button):
            button.setAutoDefault(False)
            button.setDefault(False)

        self.setTabOrder(self.title_edit, self.category_combo)
        self.setTabOrder(self.category_combo, self.year_field)
        self.setTabOrder(self.year_field, self.items_table)
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

    def _build_popup_tests_tab(self):
        self.popup_tests_tab = QWidget()
        layout = QVBoxLayout(self.popup_tests_tab)

        list_label = QLabel("Popup tests:")
        self.popup_list = QListWidget()
        self.popup_list.setAccessibleName("Popup tests")
        self.popup_list.setAccessibleDescription("Test popups for the JAWS/NVDA command Insert+B - Alt+U")
        for variant in POPUP_VARIANTS:
            self.popup_list.addItem(variant.heading)
        self.popup_list.setCurrentRow(0)
        self.popup_list.itemActivated.connect(lambda _item: self.on_open_popup_test())
        list_label.setBuddy(self.popup_list)
        layout.addWidget(list_label)
        layout.addWidget(self.popup_list)

        self.plain_text_check = QCheckBox("Report date fields as plain text")
        self.plain_text_check.setAccessibleName("Report date fields as plain text")
        self.plain_text_check.toggled.connect(self._on_plain_text_toggled)
        layout.addWidget(self.plain_text_check)

        button_layout = QHBoxLayout()
        self.open_popup_button = QPushButton("Open")
        self.open_popup_button.setAccessibleName("Open popup test")
        apply_tooltip_accessibility(
            self.open_popup_button,
            "Open the selected test popup",
            "Open the popup selected in the Popup tests list",
        )
        self.open_popup_button.setAutoDefault(False)
        self.open_popup_button.setDefault(False)
        self.open_popup_button.clicked.connect(self.on_open_popup_test)
        button_layout.addWidget(self.open_popup_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.tabs.addTab(self.popup_tests_tab, "Popup Tests")

    def _on_plain_text_toggled(self, checked: bool):
        set_date_fields_as_plain_text(checked)
        self.set_status(
            "Date fields will be reported as plain text"
            if checked
            else "Date fields will be reported as edit fields"
        )

    def focus_popup_tests(self):
        self.tabs.setCurrentWidget(self.popup_tests_tab)
        self.popup_list.setFocus()

    def on_open_popup_test(self):
        row = self.popup_list.currentRow()
        if row < 0:
            self.set_status("Select a popup test first", announce=True)
            self.popup_list.setFocus()
            return
        message = exec_popup_variant(self, POPUP_VARIANTS[row])
        self.popup_list.setFocus()
        self.set_status(message, announce=True)

    def _on_table_selection_changed(self):
        # Status text only: a focus-pulse announce on every arrow key pulls
        # focus out of the table, and JAWS/NVDA re-enters it reading coordinates.
        # The cell's AccessibleTextRole already speaks the row; Alt+/ reads this.
        row = self.items_table.currentRow()
        if row < 0:
            return
        name_item = self.items_table.item(row, 0)
        label = name_item.text() if name_item else f"Row {row + 1}"
        announce_selection(self.status_bar, label, count=1, announce=False)

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
        if not validate_year_field(self.year_field, self):
            self.set_status("Save canceled: year is not valid", announce=True)
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

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            focused = self.focusWidget()
            if isinstance(focused, QPushButton) and focused.isEnabled():
                focused.click()
                event.accept()
                return
        super().keyPressEvent(event)

    def setup_shortcuts(self):
        for seq, handler in (
            ("F1", self.on_show_shortcuts),
            ("Escape", self.on_escape),
            ("Alt+/", self.read_status),
            ("Shift+F1", self.on_context_help),
            ("Ctrl+S", self.on_save),
            ("Alt+T", lambda: self.title_edit.setFocus()),
            ("Alt+C", lambda: self.category_combo.setFocus()),
            ("Alt+Y", lambda: self.year_field.setFocus()),
            ("Alt+L", lambda: self.items_table.setFocus()),
            ("Alt+D", self.on_delete),
            ("Alt+I", self.on_open_info_dialog),
            ("Alt+P", lambda: self.plot_list.setFocus()),
            ("Alt+U", self.focus_popup_tests),
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
                ("F1", "Show keyboard shortcuts"),
                ("Shift+F1", "Context help"),
                ("Alt+/", "Read status bar"),
                ("Ctrl+S", "Save"),
                ("Alt+T", "Title"),
                ("Alt+C", "Category"),
                ("Alt+Y", "Year"),
                ("Alt+L", "Jump to list"),
                ("Alt+D", "Delete selected"),
                ("Alt+I", "Open info dialog"),
                ("Alt+P", "Plot"),
                ("Alt+U", "Popup tests"),
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
