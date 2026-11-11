# PySide6 Accessibility Patterns and Implementation Reference

This document is the code-oriented reference for the screen reader accessibility patterns in this repository's sample application. Principles live in [PySide6_Screen_Reader_Accessibility_Best_Practices.md](PySide6_Screen_Reader_Accessibility_Best_Practices.md). The mapping to the AbCS project standards is in [AbCS_Standards_Crosswalk.md](AbCS_Standards_Crosswalk.md).

Runnable sample files (repository root):
- `accessibility_patterns.py` — core helpers and `AccessibilityMixin`
- `styled_dialogs.py` — `AccessibleDialog`, F1 shortcut dialog, and message box helpers
- `main.py` — demo window `AccessibleSampleWindow` and `InfoDialog`

**Production examples.** Some sections name windows from [AbCS](https://github.com/cfdrakeNS/AbCS_Audiobook_Collector_Scanner) (Audio Book Collector Scanner), the application these patterns came from. Those are marked **AbCS production** and are not part of this repository.

## Scope

Use this document when implementing or refactoring windows, dialogs, forms, and tables in PySide6 applications.

## 1. Status announcement pattern

Goal: make status updates reliably available to screen reader users.

Pattern:
- Provide a per-window status API: `AccessibilityMixin.set_status(message, announce=False)`.
- `announce=True` briefly moves focus to the status bar so the screen reader reads it, then restores focus (`announce_status_message`). The delay depends on the detected screen reader (section 14).
- Announce only while the window is visible. `set_status` ignores `announce=True` when `self.isVisible()` is false (section 23).
- Keep a default status message for explicit readback, and support **Alt+/** to re-read the current status (`read_status_bar_message`).
- Announce only meaningful state changes, such as save, delete, or a validation failure. Do not announce on every arrow key (section 21).
- When focus is restored after the announcement, `announce_status_message` uses the application focus widget, or the window's own focus widget if the window is not active yet (section 24).

Reference: `accessibility_patterns.py` (`announce_status_message`, `read_status_bar_message`, `AccessibilityMixin.set_status`), `main.py` (`AccessibleSampleWindow.on_save`, `on_delete`).

## 2. Editable combo anti-noise pattern

Goal: prevent silent value changes and accidental edits.

Pattern:
- Install event filters on editable combos and their line edits.
- Block plain Up/Down keys when they can silently change values (events may arrive on the combo **or** its internal `lineEdit()`).
- Allow explicit dropdown actions with Alt+Down / Alt+Up (`showPopup()`).
- Use beep or equivalent feedback when blocking key input.
- When combining `AccessibilityMixin` with `QDialog` subclasses, list **`AccessibilityMixin` before the dialog base class**. Otherwise Qt's built-in `QObject.eventFilter` shadows the mixin's Python `eventFilter` and combo blocking will not run.

Reference: `accessibility_patterns.py` (`AccessibilityMixin.eventFilter`, `_should_block_combo_arrow_key`), `main.py` (`category_combo`).

## 3. Alt-key hygiene pattern

Goal: avoid stray Alt+letter input leaking into text fields.

Pattern:
- Define a per-window allowlist of Alt+letter actions (`ALLOWED_ALT_KEYS`).
- Consume unmapped Alt+letter and Alt+digit events in event filters, with a beep.
- Keep `Alt+/` available in major windows.

Reference: `accessibility_patterns.py` (`is_unmapped_alt_letter`), `main.py` (`AccessibleSampleWindow.ALLOWED_ALT_KEYS`).

## 4. AccessibleDialog window title pattern (JAWS Insert+T)

Goal: ensure screen readers read the **active dialog title**, not the window behind it.

### Problem

Qt's MSAA/UIA bridge exposes `QDialog(parent=X)` as an accessibility **child** of `X`. JAWS Insert+T walks up the tree from the focused control:

`focused_control → … → DialogWindow → MainWindow`

and reads `MainWindow`'s title instead of the dialog's.

### Solution: `AccessibleDialog`

All feature dialogs and inline help/popup dialogs inherit from `AccessibleDialog` (`styled_dialogs.py`) instead of `QDialog` directly.

Pattern:
- Pass the logical owner as `parent` to `AccessibleDialog(parent, title=...)`. The base class stores it as `owner_widget` but calls `QDialog.__init__(None)`, so the dialog is a **root** in the accessibility tree.
- On Windows, set the Win32 **owner** via `SetWindowLongPtrW(GWL_HWNDPARENT)` (`_set_win32_owner`) so taskbar grouping and z-order still follow the calling window, without creating an accessibility parent chain.
- On `showEvent`, re-fire focus so JAWS registers the new window before Insert+T is used. The delay is 100 ms on Qt 6.11 and later and 300 ms on older Qt (`_focus_refire_delay_ms`). Qt 6.11 improved MSAA/UIA window and focus registration on Windows.
- Subclasses that override `showEvent` must call `super().showEvent(event)`. Subclasses that override `done()` must call `super().done(r)`.
- When a window also uses `AccessibilityMixin`, inherit as `class MyWindow(AccessibilityMixin, AccessibleDialog)` (section 2).
- Modeless utility windows that use `AccessibleDialog` may set `self._announce_focus_on_show = False` in `__init__` to skip the focus refire when repeated `show()` calls would steal focus.

**Feature window example:**
```python
from styled_dialogs import AccessibleDialog

class InfoDialog(AccessibleDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="Sample Info Dialog")
        # ...
```

**F1 popup example:** use `exec_shortcuts_dialog(self, title, shortcuts)` (section 7), which builds an `AccessibleDialog`.

**AbCS production exception.** `ImportProgressWindow` in AbCS stays a standard `QDialog` with a Qt parent. It is a modeless scan utility that must stay above its owner through Qt z-order and handle Escape/cancel during an active scan. Keep similar utility windows on `QDialog` only when `AccessibleDialog` would break that behavior.

Reference: `styled_dialogs.py` (`AccessibleDialog`, `_focus_refire_delay_ms`, `_set_win32_owner`), `main.py` (`InfoDialog`, `AccessibleSampleWindow`).

## 5. Modal dialog accessibility pattern

Goal: make warnings, confirmations, and feature dialogs readable and actionable.

Pattern:
- Use `AccessibleDialog` for custom modal dialogs (section 4), not raw `QDialog(parent)`.
- Use the shared message box helper for prompts (section 18).
- Set clear dialog titles, text, and explicit button labels. Set accessible names and descriptions on the dialog and every control.
- Make the primary action the default button (`setDefault(True)`) and make sure Tab reaches it.
- Return focus to the most relevant control after the dialog closes (section 24).

Reference: `styled_dialogs.py`, `main.py` (`InfoDialog`, `AccessibleSampleWindow.on_open_info_dialog`).

## 6. Keyboard shortcut implementation pattern

Goal: prevent conflicts and keep shortcut behavior predictable.

Pattern:
- **F1**, **Shift+F1**, **Escape**, and **Alt+/** are always local `QShortcut`s on each window, even in an application that centralizes other shortcuts. Each window needs its own help, close, and status behavior.
- Alt+letter field shortcuts may be registered locally (as in this demo) or through a central shortcut manager in larger applications. Either way, keep the window's `ALLOWED_ALT_KEYS` in sync (section 3).
- Use one save shortcut everywhere: **Ctrl+S** runs Save. In this demo, Alt+S only moves focus to the Save button.
- Use `Qt.ShortcutContext.WidgetWithChildrenShortcut` so a window's shortcuts do not fire in other windows.
- Do not bind global Enter/Return shortcuts. They steal default-button activation.

**AbCS production.** AbCS centralizes many shortcuts in a ShortcutManager. Its policy and current status are in AbCS `doc/standards/standard_shortcuts.md` and `shortcut_centralization_status.md`. The crosswalk summarizes what to copy.

Reference: `main.py` (`AccessibleSampleWindow.setup_shortcuts`).

## 7. Accessible help dialog pattern (F1)

Goal: provide a stable, readable shortcut list.

Pattern:
- Show the list in an `AccessibleDialog`, so Insert+T reads the help title (section 4).
- Use a one-column read-only `QTableWidget`. Hide both headers, turn off the grid and hover, and set `setTabKeyNavigation(False)`.
- Each row's display text is `"action - key"`. Its `AccessibleTextRole` is `"action: key"`.
- Select the first row and put focus on the table when the dialog opens. Escape closes the dialog.
- Include **Alt+/** in every window's list.

```python
from styled_dialogs import exec_shortcuts_dialog

exec_shortcuts_dialog(
    self,
    "Keyboard Shortcuts - Accessible Sample",
    [("F1", "Show this help"), ("Alt+/", "Read status"), ("Ctrl+S", "Save")],
)
```

Reference: `styled_dialogs.py` (`exec_shortcuts_dialog`), `main.py` (`AccessibleSampleWindow.on_show_shortcuts`).

## 8. Focus safety pattern for editable fields

Goal: reduce accidental full-value overwrite.

Pattern:
- On FocusIn, defer deselect/cursor behavior with `QTimer.singleShot(0, ...)`.
- Deselect auto-selected text in line edits, combo line edits, and spin boxes.

Reference: `accessibility_patterns.py` (`AccessibilityMixin.focus_deselect`, `eventFilter` FocusIn branch).

## 9. Table accessibility pattern

Goal: JAWS and NVDA read each cell's content, not row numbers or cell coordinates, and sighted users can see the selection.

### Problem

- A cell with no `AccessibleTextRole` text, or an empty cell, makes JAWS read the cell coordinates instead of content.
- A name cell whose accessible text is only the name (for example "First item name") never speaks the value.
- Hiding the vertical header with `setVisible(False)` alone still leaves an active row header that the screen reader can read.
- Qt's default Windows 11 selection is a faint gray, and it fades further when the table loses focus.

### Solution

**Spoken text.** `set_accessible_table_rows(table, rows)` fills a label/value table from `(label, value)` pairs. Both cells in a row get the same `AccessibleTextRole`, `"label: value"`, so arrowing to either cell reads the label and value together. No cell is left empty.

**Row headers.** `configure_table(table)` silences the vertical header. It hides and disables it, removes focus, makes it non-clickable and non-highlighting, labels every section `""`, and names it "Table Row Headers".

**Selection visibility.** `configure_table` also applies `build_accessible_table_style()`, which gives the selected cell a solid `palette(highlight)` fill with `palette(highlighted-text)` and no hover change. `keep_selection_visible_when_inactive(table)` copies the active highlight colors into the inactive palette group, so the selection stays visible after Tab leaves the table.

**Behavior.** For label/value tables, use row selection, single selection, no editing, and `setTabKeyNavigation(False)`. Turn off mouse tracking and hover on the table and viewport (done by `configure_table`).

```python
from accessibility_patterns import configure_table, set_accessible_table_rows

table = QTableWidget(0, 2)
table.setHorizontalHeaderLabels(["Name", "Value"])
set_accessible_table_rows(table, [("Item 1", "100"), ("Item 2", "200")])
table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
table.setTabKeyNavigation(False)
configure_table(table)
```

Model-backed tables (`QTableView` with a `QAbstractTableModel`) follow the same rules. Return text for `Qt.AccessibleTextRole` from `data()` for every column, and return `""` from `headerData()` for the vertical orientation.

Do not announce the row through the status bar on every arrow key (section 21).

**AbCS production.** The AbCS Statistics table (`statistics_dialog.py`) uses the same label/value text on both cells and the same disabled header. The main book table (`BookTableModel` in `main_window.py`) returns `AccessibleTextRole` for every column.

Reference: `accessibility_patterns.py` (`configure_table`, `set_accessible_table_rows`, `build_accessible_table_style`, `keep_selection_visible_when_inactive`), `main.py` (`AccessibleSampleWindow._build_form_tab`).

## 10. About/Info dialog pattern

Goal: a consistent, accessible approach for About, License, Setup, and other informational dialogs.

Pattern:
- Use a dialog class (for example `InfoDialog`, AbCS `AboutDialog`, `LicenseDialog`) instead of building popups inline in the main window.
- Inherit from `AccessibleDialog`, not `QDialog` (section 4).
- Body text: `create_dialog_html_text()` with heading, body, and item blocks (section 11), never a `QLabel`.
- Size the dialog so no paragraph wraps: call `fit_dialog_width_to_text(self, body, height=...)` after building the layout (section 11).
- Footer: right-aligned buttons; the primary or Close button is the default.
- Set a **short** accessible name and a helpful accessible description on the text area.
- Set first focus to the text area in `showEvent` with `QTimer.singleShot(0, ...)` (section 23).
- Make the dialog modal and return focus to the opening control after it closes (section 24).
- Verify with JAWS Insert+T that the dialog title is read.

```python
def on_open_info_dialog(self):
    dlg = InfoDialog(self)
    dlg.exec()
    announce_dialog_closed(dlg)
    self.info_button.setFocus()
```

**AbCS production.** AbCS footer buttons also use `build_accessible_button_style()` with heights scaled by `UIScaler` (section 19). This demo uses default button styling.

Reference: `main.py` (`InfoDialog`, `AccessibleSampleWindow.on_open_info_dialog`), `accessibility_patterns.py` (`create_dialog_html_text`, `fit_dialog_width_to_text`).

## 11. Read-only navigable text pattern

Goal: let JAWS/NVDA users move through static help, About, or License text one line at a time with arrow keys.

### Problem

- `QLabel` with the full body in `setAccessibleName()` makes the screen reader dump all text at once, and arrow keys do not move line by line.
- Empty lines in the source text can make JAWS repeat the previous line.
- When a paragraph wraps onto several visual lines, JAWS reads each visual line as you arrow, then rereads the whole paragraph, so the user hears text twice.

### Solution for dialog prose: `create_dialog_html_text()`

Pass a list of `(kind, text)` blocks, where kind is `"heading"`, `"body"`, or `"item"`. Each block becomes one HTML paragraph in a read-only `QTextEdit`, so the screen reader reads each heading, line, and list item on its own.

```python
from accessibility_patterns import create_dialog_html_text, fit_dialog_width_to_text

self.body = create_dialog_html_text(
    self,
    [
        ("body", "This dialog is an accessibility root window."),
        ("heading", "WHAT TO CHECK"),
        ("item", "Insert+T reads the window title: Sample Info Dialog."),
    ],
    "Info text",  # short name only, never the full body
    "Sample information. Use arrow keys to read line by line. Press Tab to move to the buttons.",
)
layout.addWidget(self.body, stretch=1)
# ... add buttons ...
fit_dialog_width_to_text(self, self.body, height=420)
```

**No wrapping.** Keep each block to one short sentence. `fit_dialog_width_to_text()` measures every paragraph with the widget's font (including bold headings and item indents) and widens the dialog so none wraps, capped at 90% of the screen width. Call it after the layout is built.

### Solution for plain text: `create_accessible_read_only_text()`

For a short read-only text area outside a dialog (for example the demo's Text Review tab), `create_accessible_read_only_text()` loads plain text with blank lines collapsed (`_collapse_blank_lines()`).

Both helpers apply the same keyboard review settings (`configure_navigable_text_edit()`):
- `setReadOnly(True)` and `setTextInteractionFlags(Qt.TextSelectableByKeyboard)`, which enables arrow-key line review
- `setFocusPolicy(Qt.StrongFocus)` and `setTabChangesFocus(True)`
- Mouse tracking and `WA_Hover` off on the widget and viewport
- Transparent background and no frame for dialog embedding

### Rules

- **Never** put the full body text in `setAccessibleName()`. Use a short name and a description that mentions arrow-key review.
- One sentence per block; no paragraph may wrap at the dialog's width.
- Decorative graphics (for example a splash image) use `Qt.NoFocus`.
- Set initial focus to the text area in `showEvent` with `QTimer.singleShot(0, ...)`.

Reference: `accessibility_patterns.py` (`create_dialog_html_text`, `blocks_to_dialog_html`, `fit_dialog_width_to_text`, `create_accessible_read_only_text`, `configure_navigable_text_edit`), `main.py` (`InfoDialog`, `_build_text_tab`).

## 12. Plot field line-by-line review pattern

Goal: let screen reader users review long prose (for example a book plot) line by line in view mode while keeping continuous prose in storage and edit mode.

### Problem

- Read-only `QTextEdit` did not give reliable Up/Down line navigation for long prose in JAWS/NVDA.
- Putting the full text in `setAccessibleName()` made review worse.
- Splitting every sentence into list rows looked like blank lines between items and polluted stored text with extra line breaks.

### Solution: `PlotLineList`

`PlotLineList` is a `QListWidget` subclass with one row per navigable line. `set_plot_text()` loads it through `plot_lines_for_review()`:
1. **Item 0:** the rating line only (for example `Rating: 3.5 (2 ratings)`), when the text starts with `Rating:`.
2. **Items 1+:** the body split into lines of at most **73 characters**, breaking only at word boundaries (`_wrap_at_words()`).

Accessibility and visual settings:
- `setAccessibleName("Plot")` — short label only; row text comes from `AccessibleTextRole` per item.
- `setAccessibleDescription("")` — avoid duplicate announcements.
- `setSpacing(0)`, `setUniformItemSizes(True)`, zero item padding in the stylesheet.
- `_CompactPlotLineDelegate` paints single-line rows at `fontMetrics().height()` so rows stack without visual gaps.
- Selected/focused rows use the base background (no highlight bar), so the field does not flash a selection color while reviewing.
- Mouse tracking and `WA_Hover` off.

```python
from accessibility_patterns import PlotLineList

self.plot_list = PlotLineList()
self.plot_list.setAccessibleName("Plot")
self.plot_list.set_plot_text(plot_text)
```

### Rules

- Load with `PlotLineList.set_plot_text()`; do not call `setPlainText()`.
- Keep the rating on its own row (item 0).
- Do not break words when wrapping.
- Do not put the full text in `setAccessibleName()`.
- Do not inject sentence line breaks into stored text.

**AbCS production.** AbCS Book Details stacks a `PlotLineList` (view mode) and a `QTextEdit` (edit mode) in a `QStackedWidget`, and Web Metadata uses `PlotLineList` for the plot field. AbCS adds helpers this demo does not include: `format_plot_text_for_navigation()` normalizes stored prose, `set_navigable_plain_text()` loads edit mode, and `plot_text_equivalent()` compares plots ignoring whitespace. They are in AbCS `src/accessibility/read_only_text.py`.

Reference: `accessibility_patterns.py` (`PlotLineList`, `plot_lines_for_review`), `main.py` (`_build_text_tab`).

## 13. Decision policy: defect vs intentional noise reduction

Use this policy in reviews:
- Confirmed defect: required information or action is not reliably accessible.
- Intentional design: reduced announcement noise but required access remains explicit and testable.
- Needs decision: tradeoff is unclear and requires design confirmation before implementation.

## 14. Screen reader process detection pattern

Goal: gate speech-only behavior when a screen reader is likely active.

Pattern:
- Scan running processes for known screen reader executables (JAWS, NVDA, Narrator, Orca).
- Use `psutil` when available; treat missing `psutil` as "no reader detected."
- Combine process detection with `QAccessible.isActive()` before announcing status or opening readback paths.
- Use per-reader focus-restore delays when briefly moving focus to the status bar (JAWS 300 ms, NVDA 1500 ms, Narrator 3500 ms, Orca 800 ms).
- Detection can also choose a control: the year field is a typed text box when a screen reader is running (section 25).

Reference: `accessibility_patterns.py` (`get_active_screen_reader`, `is_screen_reader_active`, `get_screen_reader_focus_delay_ms`).

## 15. QAccessible initialization pattern

Goal: ensure Qt's accessibility bridge is active before windows open.

Pattern:
- Call `QAccessible.setActive(True)` at application startup.
- Call `QAccessible.setRootObject(app)` so the application object is the accessibility root.
- Run this once in `main()` before creating the primary window.

Reference: `accessibility_patterns.py` (`init_app_accessibility`), `main.py` (`main`).

## 16. Dialog lifecycle event pattern

Goal: notify screen readers when modal or feature dialogs open and close.

Pattern:
- Call `announce_dialog_opened(dialog, title)` from the dialog's `showEvent`, after `super().showEvent(event)`. It emits `QAccessible.Event.DialogStart`. Calling it before `show()` sends the event for a window the screen reader cannot see yet.
- Call `announce_dialog_closed(dialog)` after the dialog closes to emit `QAccessible.Event.DialogEnd`.
- Set a short accessible name on the dialog when a title is provided.
- Only emit events when `QAccessible.isActive()` is true.

Reference: `accessibility_patterns.py` (`announce_dialog_opened`, `announce_dialog_closed`), `main.py` (`InfoDialog.showEvent`, `AccessibleSampleWindow.showEvent`).

## 17. Tooltip vs accessible description pattern

Goal: give sighted users tooltips without overwriting screen reader descriptions.

Pattern:
- Set `setToolTip(tooltip)` for sighted hover text.
- Set `setAccessibleDescription(description)` separately for screen reader guidance.
- Use `apply_tooltip_accessibility(widget, tooltip, description)` so tooltips never replace accessible descriptions.
- For menu/toolbar actions, keep decorative icons out of accessible names.

Reference: `accessibility_patterns.py` (`apply_tooltip_accessibility`), `main.py` (Save, Delete, and Info Dialog buttons).

## 18. Styled message box pattern

Goal: make validation and confirmation boxes readable and keyboard-safe, including over another dialog.

Pattern:
- Use `exec_styled_message_box(parent, ...)` (or `show_styled_message_box`) instead of raw `QMessageBox`.
- Set the box's accessible name and description, and set accessible names and descriptions on its buttons (`button_accessibility`).
- Use decorative standard icons without putting icon text into spoken names.
- Return focus to the corrective control after validation failures (section 24).

### Message boxes over an AccessibleDialog

A modal `QMessageBox(dialog)` disables the dialog behind it, and JAWS then says "<dialog title> unavailable" before reading the box. When the parent's window is a visible `AccessibleDialog`, `exec_styled_message_box`:
1. Creates `QMessageBox(None)`, with no Qt parent, so the dialog is not disabled.
2. Sets `Qt.WindowModality.WindowModal` and the Win32 owner (`_set_win32_owner`) so the box stays above the dialog.
3. Centers the box on the owner.
4. After `exec()` returns, raises and activates the owner. Without a Qt parent, Qt does not reactivate the owner, and the caller's `setFocus()` would land in an inactive window.

A raw `QMessageBox(dialog).exec()` brings the "unavailable" noise back. In JAWS, **Insert+B** reads the whole message box.

Reference: `accessibility_patterns.py` (`exec_styled_message_box`), `styled_dialogs.py` (`show_styled_message_box`), `main.py` (`InfoDialog.on_test_message_box`, `AccessibleSampleWindow.on_save`, `on_delete`, `on_escape`).

## 19. UI scaling pattern

Goal: keep controls readable at high zoom without breaking focus or table semantics.

Pattern:
- Centralize zoom in a scaler (for example 50–300%, default 150%).
- Scale fonts, button heights, combo heights, and status bar font together.
- Apply table/combo CSS that disables hover noise and keeps focus and selection visible (section 9).
- On Linux, prefer minimal stylesheets when platform painting is fragile.

This demo sets a fixed 10 pt dialog font (`AccessibleDialog`) and uses system palette colors.

**AbCS production.** `UIScaler` (`src/accessibility/scaling.py`) and `build_accessible_button_style()` (`src/accessibility/style_helpers.py`) implement full scaling.

## 20. Help system architecture pattern

Goal: provide discoverable, context-sensitive help without accessibility noise.

Pattern:
- **F1** opens the per-window shortcut table (section 7).
- **Shift+F1** opens window-specific process help.
- Discover markdown help topics at runtime from a `help_docs/` folder, and route Shift+F1 per window through a window-to-topic map.
- In a Help window, use a nav list plus content area with an explicit Tab cycle between them.
- Keep Help-window zoom independent of global UI zoom; default Help zoom to 100% when a screen reader is active.

This demo's Shift+F1 is a stub message box (`AccessibleSampleWindow.on_context_help`).

**AbCS production.** `src/ui/help_router.py` (`install_shift_f1_help`, `show_context_help`) and the `help_docs/` folder.

## 21. Selection announcement pattern

Goal: make selection changes available without relying on visual highlighting, and without speech noise.

Pattern:
- While the user arrows through a table or list, **do not** announce through the status bar. The cell's `AccessibleTextRole` already speaks the row (section 9). A status-bar focus pulse on every arrow key pulls focus out of the table, and JAWS re-enters it reading coordinates.
- Update the status text quietly (`announce_selection(..., announce=False)`) so **Alt+/** can read it.
- Announce with `announce=True` only after an explicit selection action, such as Space or Shift+arrow multi-select, or an action like "3 selected".
- Put semantic row/cell text in `Qt.AccessibleTextRole`, not only in display text.

**AbCS production.** The AbCS main window calls `announce_selection()` only from explicit selection actions, and keeps the "selected" suffix in each cell's `AccessibleTextRole` (`BookTableModel.set_selection_book_ids`).

Reference: `accessibility_patterns.py` (`announce_selection`), `main.py` (`AccessibleSampleWindow._on_table_selection_changed`).

## 22. Tab-exits-table pattern

Goal: prevent Tab from trapping users inside large tables.

Pattern:
- Set `setTabKeyNavigation(False)`, or replace the table's `keyPressEvent` so **Tab** and **Shift+Tab** move focus to the next/previous widget in the tab chain.
- Delegate all other keys to the default `QTableWidget.keyPressEvent`.
- Pair with explicit `setTabOrder` so the exit target is predictable.

Reference: `accessibility_patterns.py` (`make_accessible_table_key_press`), `main.py` (`_build_form_tab`).

## 23. Window open lifecycle pattern

Goal: the screen reader speaks only the new window when it opens, starting at the right control.

### Problem

A status announcement made while a window is still hidden moves focus to a status bar the screen reader cannot see. Focus lands on the window behind, and the screen reader reads that window's title instead of the new one.

### Pattern

- Pass starting values (for example a collection or filter) through the constructor. Do not change combos after construction.
- Never announce while the window is hidden. `AccessibilityMixin.set_status` ignores `announce=True` when `isVisible()` is false. Call sites in production code may pass `announce=self.isVisible()` explicitly.
- If an opening message must be spoken, keep it and announce it after `showEvent`.
- Emit `DialogStart` from `showEvent` (section 16).
- Set first focus in `showEvent` with `QTimer.singleShot(0, ...)`. `AccessibleDialog` then re-fires focus after its delay (section 4).
- Guard one-time work with a flag, because `showEvent` runs again when a minimized window is restored.

```python
def showEvent(self, event):
    super().showEvent(event)
    if self._shown_once:
        return
    self._shown_once = True
    announce_dialog_opened(self, self._window_title)
    QTimer.singleShot(0, lambda: self.title_edit.setFocus(Qt.FocusReason.OtherFocusReason))
```

Reference: `main.py` (`AccessibleSampleWindow.showEvent`, `InfoDialog.showEvent`), `accessibility_patterns.py` (`AccessibilityMixin.set_status`).

## 24. Focus restore after modal dialogs and message boxes

Goal: after any modal closes, focus returns to a sensible control and the screen reader reads it.

Pattern:
- After a feature dialog closes, set focus on the control that opened it (for example `self.info_button.setFocus()`), or on the title or table, as the parent window already does.
- After a validation message box, set focus on the field that needs correcting, then announce the status.
- A message box over an `AccessibleDialog` has no Qt parent, so `exec_styled_message_box` reactivates the owner itself (section 18).
- Window activation is asynchronous. Right after a box closes, `QApplication.focusWidget()` can be `None` even though the window remembers its focus widget. `announce_status_message` falls back to `status_bar.window().focusWidget()`, so the status announcement returns focus to the field instead of leaving it on the status bar.

Reference: `accessibility_patterns.py` (`exec_styled_message_box`, `announce_status_message`), `main.py` (`on_save`, `on_delete`, `on_open_info_dialog`, `InfoDialog.on_test_message_box`).

**AbCS production.** AbCS uses `restore_main_focus_after_modal` in the main window.

## 25. Screen reader year field pattern

Goal: a year field that reads back reliably with a screen reader, and keeps the familiar spin box for sighted users.

### Problem

A `QSpinBox` announces every Up/Down step, and the value can change silently while the user reviews the field.

### Pattern

`make_year_field(parent, min_year=None, max_year=None)` returns:
- **Screen reader running:** `MaskedYearEdit`, a plain `QLineEdit` with a `yyyy` placeholder and at most 4 characters. Blank means no year. Its accessible description states the valid range. On focus, it deselects and puts the cursor at the start.
- **No screen reader:** a `QSpinBox` limited to the range.

Both expose `setValue()` and `value()`. The default range is 1801 through the current year (`default_year_range()`).

Before saving, call `validate_year_field(field, parent)`. For the typed field, it parses with `parse_year_text()`. If the value is invalid, it beeps, shows a styled warning that includes the text entered (for example "Year '20' is not valid. Enter a year from 1801 to 2026, or leave blank."), puts focus back on the field, and returns `False`. The typed text is not cleared, so the user can correct it.

```python
self.year_field = make_year_field(self)
self.year_field.setValue(datetime.now().year)
self.year_field.setAccessibleName("Year field")

# in on_save
if not validate_year_field(self.year_field, self):
    self.set_status("Save canceled: year is not valid", announce=True)
    return
```

Detection runs once, when the field is created (section 14).

**AbCS production.** `src/accessibility/masked_date_fields.py` (`MaskedYearEdit`, `make_year_field`, `validate_year_spin`) reads the range from Preferences and adds a matching typed date field, `MaskedDateEdit`.

Reference: `accessibility_patterns.py` (`make_year_field`, `MaskedYearEdit`, `validate_year_field`, `parse_year_text`), `main.py` (`_build_form_tab`, `on_save`).

## 26. Menu-open focus hold pattern (AbCS production)

Goal: when a keyboard-chosen menu item opens a window, the screen reader speaks only the new window.

Problem: when the menu closes, focus returns to the main window's table for a moment, and the screen reader says "book table" before the new window appears.

Pattern: the main window holds focus on the menu bar while a keyboard-chosen menu item runs. Menus created in the main menu builder are covered automatically. A menu created elsewhere must connect its `aboutToHide` signal the same way. Do not add per-window workarounds.

This demo has no menu bar. **AbCS production:** `_hold_focus_for_menu_action` in `src/ui/main_window.py`.

## 27. QAction accessible names

`QAction` menu items use their menu text as the spoken name. Do not call `setAccessibleName` on a `QAction`; Qt does not support it. Give each action clear menu text, and keep decorative icons out of it (section 17).

## 28. Progress windows, modal completion, and worker threads (AbCS production)

Principles from AbCS background work (import, web fetch, Calibre):
- **Opening a progress window:** show, raise, activate, and focus the progress window **before** disabling the caller's buttons. Disabling the focused button first moves focus to the next control, for example an instructions label, and the screen reader reads it.
- **Modal completion after background work:** `raise_()`, `activateWindow()`, and focus on the **default button** before announcing.
- **Worker threads must not touch widgets.** Send progress and UI updates through a GUI-thread `QObject` bridge, connected with `Qt.QueuedConnection` to `@Slot` methods. Plain Python callables are not enough.

This demo has no background work.

## 29. Testing gate (manual JAWS/NVDA smoke)

Before marking a UI change done, test with at least one screen reader, and with two when possible:

1. Tab through every new control. Each speaks a useful name, and a value where it has one.
2. Activate the primary action and Cancel/Close with the keyboard only, including any Alt+letter shortcut.
3. Alt+/ reads the latest status after a meaningful action.
4. Focus returns to a sensible place after each dialog or message box closes.
5. Insert+T reads the new window's title, not the window behind it. Only the new window is spoken when it opens.
6. A confirm or validation box over a dialog is not preceded by "<title> unavailable". Insert+B reads the box.
7. Arrowing through a table reads cell content, not coordinates or row numbers.
8. Arrowing through dialog text reads each line once, with no repeated wrapped lines.

The demo exercises every item: `InfoDialog` (Test message box button), the Items table, Save with an empty title or an invalid year, Delete with no row, F1, and Escape.
