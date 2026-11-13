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
- Keep shortcut hints out of status messages ("Saved", not "Saved. Press Ctrl+S to save again"). Hints belong in accessible descriptions and the F1 list. The one exception is "Press Escape to cancel" or "Esc to close" while a long operation runs. AbCS Find and Recently Added add "Alt+/ read status" to the on-screen status only when a screen reader is running.
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
- Consume unmapped Alt+letter and Alt+digit events in event filters, and always beep. Beep from one shared place (here `AccessibilityMixin.eventFilter`), not in each window, so every window gives the same feedback. `is_unmapped_alt_letter` only answers the question; it does not beep.
- Keep `Alt+/` available in major windows.

Reference: `accessibility_patterns.py` (`is_unmapped_alt_letter`, `AccessibilityMixin.eventFilter`), `main.py` (`AccessibleSampleWindow.ALLOWED_ALT_KEYS`).

## 4. AccessibleDialog window title pattern (JAWS/NVDA command Insert+T)

Goal: ensure screen readers read the **active dialog title**, not the window behind it.

### Problem

Qt's MSAA/UIA bridge exposes `QDialog(parent=X)` as an accessibility **child** of `X`. The JAWS/NVDA command Insert+T walks up the tree from the focused control:

`focused_control → … → DialogWindow → MainWindow`

and reads `MainWindow`'s title instead of the dialog's.

### Solution: `AccessibleDialog`

All feature dialogs and inline help/popup dialogs inherit from `AccessibleDialog` (`styled_dialogs.py`) instead of `QDialog` directly.

Pattern:
- Pass the logical owner as `parent` to `AccessibleDialog(parent, title=...)`. The base class stores it as `owner_widget` but calls `QDialog.__init__(None)`, so the dialog is a **root** in the accessibility tree.
- On Windows, set the Win32 **owner** via `SetWindowLongPtrW(GWL_HWNDPARENT)` (`_set_win32_owner`) so taskbar grouping and z-order still follow the calling window, without creating an accessibility parent chain.
- On `showEvent`, re-fire focus so the new window is registered before the JAWS/NVDA command Insert+T is used. The delay is 100 ms on Qt 6.11 and later and 300 ms on older Qt (`_focus_refire_delay_ms`). Qt 6.11 improved MSAA/UIA window and focus registration on Windows. That command reads the window title. It is not an application shortcut.
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
- Set clear dialog titles, text, and explicit button labels. Set accessible names and descriptions on the dialog and every control. Do not clear the dialog's name or description to reduce speech.
- Return focus to the most relevant control after the dialog closes (section 24). After No on an unsaved-changes prompt, that control is the field the user was editing.
- With focus in a text field, the read-dialog command reads the window title and that field. Put the dialog's instructions in the field's accessible description. Start focus on a button or combo when that command must read the whole dialog. AbCS does this on the read date and Recently Added dialogs.

### Default button and Enter

Choose one rule per window:
- **One clear main action** (a confirmation, an info dialog with Close or OK): make it the default button with `setDefault(True)`, and make sure Tab reaches it. Enter anywhere in the dialog runs it.
- **A form with several buttons** (Save, Delete, Browse, and so on): turn `setAutoDefault(False)` and `setDefault(False)` off on every button, and make Enter click the button that has focus. Otherwise Enter in a text field fires whichever button Qt picks, and Enter on a focused button with auto-default off does nothing.

```python
def keyPressEvent(self, event):
    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
        focused = self.focusWidget()
        if isinstance(focused, QPushButton) and focused.isEnabled():
            focused.click()
            event.accept()
            return
    super().keyPressEvent(event)
```

Never bind a global Enter shortcut (section 6).

Reference: `styled_dialogs.py`, `main.py` (`InfoDialog` uses a default Close button; `AccessibleSampleWindow` is a form and uses Enter-clicks-focused).

## 6. Keyboard shortcut implementation pattern

Goal: prevent conflicts and keep shortcut behavior predictable.

Pattern:
- **F1**, **Shift+F1**, **Escape**, and **Alt+/** are always local `QShortcut`s on each window, even in an application that centralizes other shortcuts. Each window needs its own help, close, and status behavior.
- Alt+letter field shortcuts may be registered locally (as in this demo) or through a central shortcut manager in larger applications. Either way, keep the window's `ALLOWED_ALT_KEYS` in sync (section 3).
- Use one save shortcut everywhere: **Ctrl+S** runs Save. Do not also bind Alt+S to the Save button. AbCS does the same: Save is Ctrl+S in every window that has a Save button.
- Use `Qt.ShortcutContext.WidgetWithChildrenShortcut` so a window's shortcuts do not fire in other windows.
- Do not bind global Enter/Return shortcuts. They steal default-button activation.

**AbCS production.** AbCS centralizes many shortcuts in a ShortcutManager. Its policy and current status are in AbCS `doc/standards/standard_shortcuts.md` and `shortcut_centralization_status.md`. The crosswalk summarizes what to copy.

Reference: `main.py` (`AccessibleSampleWindow.setup_shortcuts`).

## 7. Accessible help dialog pattern (F1)

Goal: provide a stable, readable shortcut list.

Pattern:
- Show the list in an `AccessibleDialog`, so the JAWS/NVDA command Insert+T reads the help title (section 4).
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

**Behavior.** For label/value tables, use row selection, single selection, no editing, and `setTabKeyNavigation(False)`. Turn off mouse tracking and hover on the table and viewport (done by `configure_table`). Call `select_first_cell_when_focused(table)` so the first cell is highlighted when focus enters a table that has no current cell. A later visit keeps the cell the user already chose.

```python
from accessibility_patterns import (
    configure_table,
    select_first_cell_when_focused,
    set_accessible_table_rows,
)

table = QTableWidget(0, 2)
table.setHorizontalHeaderLabels(["Name", "Value"])
set_accessible_table_rows(table, [("Item 1", "100"), ("Item 2", "200")])
table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
table.setTabKeyNavigation(False)
configure_table(table)
select_first_cell_when_focused(table)
```

Model-backed tables (`QTableView` with a `QAbstractTableModel`) follow the same rules. Return text for `Qt.AccessibleTextRole` from `data()` for every column, and return `""` from `headerData()` for the vertical orientation.

Do not announce the row through the status bar on every arrow key (section 21).

**AbCS production.** The AbCS Statistics table (`statistics_dialog.py`) uses the same label/value text on both cells and the same disabled header. The main book table (`BookTableModel` in `main_window.py`) returns `AccessibleTextRole` for every column. Selecting many rows uses one selection range per run of consecutive rows (`rows_to_selection` in `table_selection.py`), not one range per cell.

Reference: `accessibility_patterns.py` (`configure_table`, `select_first_cell_when_focused`, `set_accessible_table_rows`, `build_accessible_table_style`, `keep_selection_visible_when_inactive`), `main.py` (`AccessibleSampleWindow._build_form_tab`).

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
- Verify with the JAWS/NVDA command Insert+T that the dialog title is read. This is a screen reader command, not an application shortcut.

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
        ("item", "The JAWS/NVDA command Insert+T reads the window title: Sample Info Dialog."),
    ],
    "Info text",  # short name only, never the full body
    "Sample information. Use arrow keys to read line by line. Press Tab to move to the buttons.",
)
layout.addWidget(self.body, stretch=1)
# ... add buttons ...
fit_dialog_width_to_text(self, self.body, height=420)
```

**No wrapping.** Keep each block to one short sentence. `fit_dialog_width_to_text()` measures every paragraph with the widget's font (including bold headings and item indents) and widens the dialog so none wraps, capped at 90% of the screen width. Call it after the layout is built. Do not use `QTextDocument.idealWidth()` for this; inside a `QTextEdit` it returns the current wrapped width.

**AbCS production.** `prepare_dialog_prose()` in AbCS `src/accessibility/dialog_prose.py` goes one step further for long text (About, License, Setup): it splits any block that would still pass the screen-width cap at sentence, semicolon, comma, or word boundaries, turns wrapping off, and sizes the dialog. JAWS and NVDA testing confirmed each line is then read once.

### Solution for plain text: `create_accessible_read_only_text()`

For a short read-only text area outside a dialog (for example the demo's Text Review tab), `create_accessible_read_only_text()` loads plain text with blank lines collapsed (`_collapse_blank_lines()`).

Both helpers apply the same keyboard review settings (`configure_navigable_text_edit()`):
- `setReadOnly(True)` and `setTextInteractionFlags(Qt.TextSelectableByKeyboard)`, which enables arrow-key line review
- `setFocusPolicy(Qt.StrongFocus)` and `setTabChangesFocus(True)`
- Mouse tracking and `WA_Hover` off on the widget and viewport
- Transparent background and no frame for dialog embedding

### Rules

- Do not put body text in `setAccessibleName()`. Use a short name and a description that mentions arrow-key review.
- **Exception: short instructions.** A focusable instruction label of 1 to 3 sentences may carry its whole text as its accessible name, so the screen reader reads it at once when Tab reaches it. Do not set text interaction flags on it (that switches Qt to line-by-line text reading). Anything longer uses line review.
- One sentence per block; no paragraph may wrap at the dialog's width. A help viewer whose text cannot fit may wrap, but still keeps one sentence per paragraph.
- Decorative graphics (for example a splash image) use `Qt.NoFocus`. An image that carries information (for example a cover that may be missing) takes focus and has a spoken name such as "Book cover" or "No cover".
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
- `QAccessible.isActive()` is not a screen reader test. On Windows it turns on for any UI Automation client, including Magnifier and the touch keyboard. Use the two checks this way:
  - **Changing the interface** (a typed field instead of a spin box, hiding visual-only content): process detection only (`is_screen_reader_active()`).
  - **Announcements** (status focus pulse, Alt+/ readback): `QAccessible.isActive()` or process detection, so speech still works with a reader the process list does not know.
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
- Speech of the window behind a dialog, when the dialog closes, is expected. Treat it as a bug only when that speech cuts off a message the user still needs, or when focus goes to the wrong window. If the message must survive the close, store it and announce it after focus is back. AbCS Web Metadata does this with `saved_message`.

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

Before the box opens, let the owner finish becoming active. Right after another dialog closes, no window is active yet, or Qt still reports the hidden dialog as active. If the box opens in that gap, the owner becomes active afterward and the screen reader reads the owner instead of the box. When no visible window is active, raise and activate the owner and process events, then open the box. `exec_styled_message_box` does this first, in `_settle_owner_activation` (the same name as in AbCS `src/accessibility/style_helpers.py`). Any other popup or progress window opened at that moment needs the same step.

Escape answers the same as Cancel. When the message has no Cancel, Escape answers the same as No. To show Yes and No only, include Cancel in the standard buttons, set it as the escape button, and hide it, so Escape does not fall through to Yes or No. AbCS passes that hidden button as `escape_only_button`. One Enter closes a validation warning. Escape on that warning does not also open the unsaved-changes prompt. Escape and the window's close box both run the unsaved-changes check.

A raw `QMessageBox(dialog).exec()` brings the "unavailable" noise back. The read-dialog command reads a message box in full. On a dialog whose focus is in a text field, it reads the title and that field (section 5).

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

**Exception: stepped values.** When Up/Down changes the value of a focused field (a year spin box, a date), announce the new value ("Year 2024"). The field's own value change is often not spoken, and the user needs to hear the result of each step. This applies to value fields only, never to moving through a table or list.

**AbCS production.** The AbCS main window calls `announce_selection()` only from explicit selection actions, and keeps the "selected" suffix in each cell's `AccessibleTextRole` (`BookTableModel.set_selection_book_ids`).

Reference: `accessibility_patterns.py` (`announce_selection`), `main.py` (`AccessibleSampleWindow._on_table_selection_changed`).

## 22. Tab-exits-table pattern

Goal: prevent Tab from trapping users inside large tables.

Pattern:
- Set `setTabKeyNavigation(False)`, or replace the table's `keyPressEvent` so **Tab** and **Shift+Tab** move focus to the next/previous widget in the tab chain.
- Delegate all other keys to the default `QTableWidget.keyPressEvent`.
- Pair with explicit `setTabOrder` so the exit target is predictable.
- If Tab would leave the table and the next control is hidden, keep focus on the current cell. Leaving the table with nowhere to land puts focus nowhere. The AbCS main table does this when no footer button is showing.

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
- Set first focus in `showEvent` with `QTimer.singleShot(0, ...)`, never in the constructor and never with a longer timer started from `__init__`. A timer started in `__init__` can fire after a fast close and focus a deleted widget. `AccessibleDialog` then re-fires focus after its delay (section 4).
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
self.year_field.setAccessibleName("Year")

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

`QAction` has no `setAccessibleDescription` in PySide6 either. Put the longer explanation in `setStatusTip()`.

**AbCS production menu and toolbar patterns:**
- **Filters and sort as menus.** Exclusive, checkable menu groups (View menu) replace filter combos above the table. Each item is reachable with the arrow keys and is spoken with its checked state.
- **Toolbar toggles show real state.** Checkable toolbar buttons are synced with `blockSignals` whenever the filter changes elsewhere, so the screen reader says "pressed" correctly. When a click opens a dialog instead of toggling, the button's state is put back.
- **Shortcut hints in menu text.** Write `"&Find...\tCtrl+F"` to show the key in the menu without creating a second `QShortcut`, which would cause an ambiguous-shortcut error.
- **Keys that must work from dialogs** use `Qt.ShortcutContext.ApplicationShortcut` (for example import and zoom reset).
- **Disabled menu items stay reachable** (section 35).
- **Qt 6.3:** `QAction.triggered(bool)` always passes `False`; read `isChecked()` instead.

Reference: AbCS `src/ui/main_window.py` (menu builder), `src/accessibility/style_helpers.py` (status tip for actions).

## 28. Progress windows, modal completion, and worker threads (AbCS production)

Principles from AbCS background work (import, web fetch, Calibre):
- **Opening a progress window:** show, raise, activate, and focus the progress window **before** disabling the caller's buttons. Disabling the focused button first moves focus to the next control, for example an instructions label, and the screen reader reads it. If a confirm box just closed, let that window finish becoming active before the progress window opens (section 18). The progress window is the next thing spoken.
- **Modal completion after background work:** `raise_()`, `activateWindow()`, and focus on the **default button** (or the main action button) before announcing.
- **Worker threads must not touch widgets.** Send progress and UI updates through a GUI-thread `QObject` bridge, connected with `Qt.QueuedConnection` to `@Slot` methods. Plain Python callables are not enough.

This demo has no background work. Section 39 adds what JAWS and NVDA testing of AbCS confirmed about progress windows.

## 29. Testing gate (manual JAWS/NVDA smoke)

Before marking a UI change done, test with at least one screen reader, and with two when possible:

1. Tab through every new control. Each speaks a useful name, and a value where it has one.
2. Activate the primary action and Cancel/Close with the keyboard only, including any Alt+letter shortcut.
3. Alt+/ reads the latest status after a meaningful action.
4. Focus returns to a sensible place after each dialog or message box closes.
5. The JAWS/NVDA command Insert+T reads the new window's title, not the window behind it. Only the new window is spoken when it opens.
6. A confirm or validation box over a dialog is not preceded by "<title> unavailable". The JAWS/NVDA command Insert+B reads the dialog.
7. Arrowing through a table reads cell content, not coordinates or row numbers.
8. Arrowing through dialog text reads each line once, with no repeated wrapped lines.
9. Up or Down on a year or date field speaks the new value. Arrowing a table or list does not fire a status announcement for that move.
10. An unavailable action says why. Escape and the window's close box both run the unsaved-changes check.

The demo exercises items 1–8: `InfoDialog` (Test message box button), the Items table, Save with an empty title or an invalid year, Delete with no row, F1, and Escape. Items 9 and 10 apply to windows with stepped value fields and unsaved-changes prompts (sections 32 and 18).

## Patterns from AbCS production (sections 30–41)

The sections below come from an audit of every accessibility workaround in AbCS (November 2026) and from the JAWS and NVDA retest of AbCS 3.1. They are not in this demo. File names are in the AbCS repository. Use them as patterns; copy the code from AbCS when you need it.

## 30. Re-reading content that changed under focus

Goal: the screen reader reads a field again when its content changes while it has focus.

Problem: when Page Down loads the next record into the same window, focus does not move, so JAWS and NVDA do not read the new title.

Pattern (AbCS Book Details, after paging):
1. Briefly make the read-only field editable, and clear its accessible name and description.
2. `clearFocus()`, then `setFocus(Qt.FocusReason.TabFocusReason)`, and put the cursor at the start.
3. After `max(screen reader delay, 400)` ms, make it read-only again. Check the widget still exists first.

Related:
- In a read-only viewer that loads a new document (Help), fire `QAccessible` `TextCaretMoved` after loading or jumping, and update the window title and accessible name to the new topic.
- Names and descriptions that follow state: a Play/Pause button renamed when playback changes; a description shown only in edit mode; error text placed in the description of the errors field; names cleared on labels that are hidden.

Reference: AbCS `src/ui/book_details.py`, `src/ui/help_window.py`, `src/ui/preview_window.py`.

## 31. Focus-out validation and loading guards

Goal: validation on leaving a field never fires because of an announcement, a message box, or code that fills the form.

Problems:
- A status announcement briefly moves focus to the status bar. A focus-out check sees that as leaving the field.
- A message box takes focus from the field, so its focus-out check runs again and stacks a second box.
- Filling fields from code fires change signals that mark the form changed, announce, or validate.

Pattern:
- Run focus-out checks one event-loop turn later (`QTimer.singleShot(0, ...)`), so Qt reports where focus went. Skip the check if focus is still in the field or its popup (for example a calendar).
- While an announcement is speaking, pause focus-out checks with a guard. AbCS uses a 2-second token; only the latest token counts, and a Tab that happened during the pause runs its commit when the pause ends.
- While a message box is open for a field, ignore that field's focus-out. One warning per problem: AbCS 3.1 removed a second year box that used to stack behind the first.
- While loading a record, set a loading flag and `setUpdatesEnabled(False)`, and `blockSignals` on widgets you change from code. Nothing marks changed, announces, or validates.
- Ignore the spurious `editTextChanged` an editable combo sends when it gets focus. Act on `activated`, not `currentIndexChanged`, for user choices.
- Save pending edits on Ctrl+S or when paging to another record, because focus-out never fired.

Reference: AbCS `src/ui/book_details.py`, `src/ui/import_detail_window.py`, `src/ui/update_window.py`.

## 32. Date and stepped-value fields

Goal: date and number fields that speak their value and never show a nonsense date.

Pattern:
- **Typed fields with a screen reader.** `make_year_field()` and `make_date_field()` return a typed `QLineEdit` (`MaskedYearEdit`, `MaskedDateEdit`) when a screen reader process is running, and a spin box or `QDateEdit` otherwise (section 25). Typed fields accept `yyyyMMdd` without dashes and ignore stray spaces.
- **Speak each step.** After Up/Down changes a focused year or date, announce the new value ("Year 2024"). This is the exception in section 21.
- **Alt+Up/Down** steps a classic date field by one day. Handle `ShortcutOverride` as well as `KeyPress`.
- **Step from blank** goes to today or this year, not the minimum (1752).
- **Tab leaves a `QDateEdit`** instead of moving between its year, month, and day parts. Override `focusNextPrevChild`.
- **Blank date.** Store blank as the minimum date and set a **non-empty** `specialValueText` (one space). An empty special value is ignored, and the screen reader reads "1752-09-14". Set it again after changing the maximum date. Add a Clear button, because the keyboard cannot clear a `QDateEdit`.
- **Validation.** Beep, show a styled warning that quotes what was typed (or "(blank)"), keep the text, and put focus back on the field. Never restore an out-of-range stored value, or the warning repeats on every focus-out. A dialog's OK refuses to close on an invalid date.
- **Prefilled typed field:** select all with `singleShot(0)` so typing replaces it.
- **Instructions:** when a small dialog opens on a date field, put its instructions in the field's accessible description (section 5).

Reference: AbCS `src/accessibility/masked_date_fields.py`, `src/ui/book_details.py`, `src/ui/main_window.py` (read date and Recently Added dialogs).

## 33. Read-only and noisy controls

Goal: no control changes its value without the user knowing.

Pattern:
- **Mouse wheel** is blocked on combos, spin boxes, and sliders inside scrolling forms.
- **Plain Up/Down** is blocked on every combo, editable or not; Alt+Up/Down opens the list (section 2).
- **Read-only combo.** `QComboBox` has no read-only mode. Keep it enabled and focusable, block wheel, mouse clicks, Up/Down, Space, F4, and Page Up/Down in an event filter, and add "Read only." to its description.
- **Display values** use read-only `QLineEdit` fields, which stay in the Tab order and can be reviewed, not `QLabel`.
- **Keys a field swallows.** When a window uses Page Up/Down for previous and next record, take those keys back from spin, date, and combo fields in an event filter, before the field changes its value.
- **Escape on an open combo list** closes the list first, not the dialog.
- **Alt+letter on a combo** focuses it and opens its list.

Reference: AbCS `src/ui/book_details.py`, `src/ui/import_detail_window.py`, `src/ui/preferences_window.py`, `src/ui/help_window.py`.

## 34. View and edit modes, and dynamic Tab order

Goal: Tab reaches exactly the controls the user can see and use.

Pattern:
- **View and edit stacks.** A read-only field in view mode and a combo in edit mode share one cell in a `QStackedWidget`. Swap the focus proxy with the page. Hidden pages are `NoFocus`, and their signals never mark the form changed.
- **Rebuild the Tab chain** from visible, enabled widgets whenever visibility changes: mode switch, buttons shown or hidden, and again after an announcement has finished (AbCS waits `max(350, screen reader delay + 50)` ms).
- **Buttons hidden by mode** are removed from the chain. Their shortcuts only fire while the button is visible, and the window's Alt allowlist and F1 list follow what is visible.
- **No empty Tab stops.** Scroll areas and their content widgets are `NoFocus`. The main window frame is not a Tab stop; in AbCS before 3.1, Tab past the last footer button went nowhere.
- **Explicit `setTabOrder`** for whole forms, not only around tables. One Tab goes from a tab page's instructions to its first setting.
- **Custom order where Qt skips controls.** The AbCS Listen window forces Tab through Rewind and Forward, which Qt and JAWS otherwise skipped, and Left/Right move between the player buttons with wraparound.
- **`setTabChangesFocus(True)`** on every `QTextEdit`, or Tab is typed into it.

Reference: AbCS `src/ui/book_details.py`, `src/ui/web_metadata.py`, `src/ui/preview_window.py`, `src/ui/main_window.py`.

## 35. Keeping unavailable actions findable

Goal: screen reader users can find every command and learn why it does not work right now.

Pattern:
- **Disabled menu items stay in the arrow-key list.** A `QProxyStyle` returns 1 for `QStyle.StyleHint.SH_Menu_AllowActiveAndDisabled`, so JAWS and NVDA read them as "unavailable" and the list length does not change. Build the proxy on a fresh style instance (`QStyleFactory.create(name)`), because `QProxyStyle` takes ownership of its base style. Style the highlighted disabled item so sighted users see where the arrow keys are.
- **Prefer enabled buttons that explain.** A disabled button drops out of the Tab order. Keep it enabled, and when it is pressed, show a message or status that explains what is missing. AbCS Import keeps Scan enabled and reports missing fields in a popup.
- **A shortcut for an unavailable action says why**, for example "Browse is available in Edit mode."
- **A disabled button's description gives the reason**, for example "Listen is unavailable while editing. Save or cancel first."
- **Enter that does nothing says why** (for example on a column that has no action).

Reference: AbCS `src/accessibility/accessible_app_style.py` (`AccessibleAppStyle`), `src/main.py`, `src/ui/book_details.py`, `src/ui/import_window.py`.

## 36. Records, reloads, and large selections

Goal: focus stays on the record the user was working with, and selection stays fast.

Pattern:
- **Focus a table only with a valid current, selected cell.** Otherwise the screen reader lands on a table with nothing to read.
- **Keep focus on the same record across reloads and sorts.** Block signals on the view, selection model, and model; turn updates off; remember the record ID; rebuild; restore the current cell by ID; then restore again with a token-guarded `singleShot(0)` in case a later event moved it.
- **After delete,** focus the next record (or the previous one at the end), and cancel the refresh's own focus restore.
- **Repaint in place** instead of a full refresh when only a cell's text changed.
- **Guard programmatic selection** with a flag, so selection handlers do not announce while code selects rows.
- **Update `AccessibleTextRole` before moving the current cell**, so the screen reader reads the new text for the new row.
- **Large selections.** Select one range per run of consecutive rows (`rows_to_selection`), not cell by cell. AbCS measured about 130 ms per Shift+Arrow step at 300 rows cell by cell.
- **Column jumps** (Alt+1 to Alt+7) move the current cell like Left/Right so the highlight follows, without changing the selection.
- **Selection mode.** While rows are selected, actions that would leave the selection say why ("Selection is active. Escape to cancel selection."). Escape clears the selection first, and says "Selection cleared".
- **Moving between records inside one dialog.** Page Up/Down loads the previous or next record into the same window and keeps a stable title, instead of closing and reopening (which speaks dialog closed and opened each time).
- **Copy.** Ctrl+C copies the cell and says "Copied." A context menu with an accessible name opens from the Menu key as well as right-click.
- **Sort and filter changes** are announced ("Sorted by name, A to Z") and move focus to the first visible row. An empty table says "No rows in the list." instead of taking focus.

Reference: AbCS `src/ui/main_window.py` (`focus_book_by_id`, `jump_to_column`, `_block_if_selecting`), `src/ui/table_selection.py` (`rows_to_selection`), `src/ui/name_list_window.py`, `src/ui/import_detail_window.py`, `src/ui/table_clipboard.py`.

## 37. Find and filter

Goal: searching a list never traps or interrupts the user.

Pattern (AbCS Name List and main window Find):
- Typing a letter while the list has focus goes to the Find field. Ctrl, Alt, and Meta chords, and modifier keys alone, stay on the list, so Ctrl+C still copies.
- The live filter updates the status bar quietly while typing; it does not announce on each key.
- Enter in Find jumps to the best match, focuses the list, and announces the position ("match 1 of 4"). Escape clears the filter and returns to the list. Ctrl+F clears Find and focuses it.
- No match: beep, announce, show a message box, then put focus back on the table.
- Help search: the search scope follows where focus was (all topics or the current topic), the search box's accessible name says the scope, results replace the navigation list, F3 and Shift+F3 find next and previous, and Escape clears the search.

Reference: AbCS `src/ui/name_list_window.py`, `src/ui/main_window.py` (Find dialog), `src/ui/help_window.py`.

## 38. Tabbed windows

Goal: tab pages are as easy to move between as windows.

Pattern (AbCS Preferences and Reading History):
- Give the `QTabWidget` an accessible name and each tab a readable name ("Display Settings").
- Ctrl+Tab and Ctrl+Shift+Tab switch tabs from anywhere in the window, with wraparound.
- On a tab change, move focus to that tab's instructions or its table.
- Each tab may start with a short focusable instruction label (section 11 exception).
- Alt+letter jumps to a section: switch tab, `ensureWidgetVisible` on the scroll area, and focus the first control.

Reference: AbCS `src/ui/preferences_window.py`, `src/ui/reading_history_window.py`.

## 39. Long operations

Goal: during a scan, import, or fetch, the progress window is what the user hears, and the keys keep working.

Confirmed in the AbCS 3.1 retest:
- **The progress window is the next thing spoken.** Show, raise, activate, and focus it before disabling the caller's controls (section 28). Import Book List spoke its own window until this order was fixed.
- **Speak each step once.** Batch web fetch showed each book's line twice (above and below the progress bar) and copied it into the dialog description, so JAWS read it twice and fell behind. Show the line once, keep the status bar only for Alt+/, and do not copy progress text into descriptions.
- **End on the progress window.** When the work finishes, keep the progress window open with a summary that starts with "Scan complete" or "Import complete", give the progress bar the same spoken name, and let Escape close it. A separate "completed" popup was replaced.

Also in AbCS:
- **Synchronous loops** (no worker thread): update the progress UI at most every 150 ms (always on the last step) and call `processEvents()`, so Escape and Alt+/ keep working.
- **Modal owner and modeless progress.** When the owner window is application-modal, forward Escape and Alt+/ from the owner to the progress window.
- **Cancel** asks first (default No), and the progress window stays open after a cancel with the summary.
- **While running,** keep focus on the progress bar unless Alt+/ is speaking, and end the status with "Press Escape to cancel".
- **Announce from `showEvent`.** A Python override of `show()` is skipped when the dialog is opened with `exec()`.
- **Batch summary.** Escape or the close box asks before discarding fetched results that were not saved.

Reference: AbCS `src/ui/import_window.py`, `src/ui/import_progress_window.py`, `src/ui/book_list_import_window.py`, `src/ui/batch_web_fetch_progress.py`, `src/ui/web_fetch_progress.py` (`FetchStatusLabel`), `src/ui/batch_web_fetch_summary.py`.

## 40. Custom accessible interfaces and media

Goal: a control whose default spoken value is meaningless gets a useful one.

Pattern (AbCS Listen window):
- **Custom slider interface.** Register a factory with `QAccessible.installFactory()` that returns a `QAccessibleWidget` subclass for the seek slider. Its name reads the position as time ("Play position 1:23 / 10:00"), and its value interface returns nothing, so the screen reader does not also say the seconds.
- **Events only for user actions.** Send `NameChanged` when the user seeks, never on playback ticks, and only to the focused control. Guard against the loop between the player's position updates and the slider.
- **A speaking status label.** A label whose text change also sets its accessible name and description and sends `NameChanged` and `DescriptionChanged` (AbCS `FetchStatusLabel`).
- **Pause media before any prompt,** so the audio does not talk over the screen reader. Alt+F4 and the close box go through the same exit path as Escape.
- **Slider values** in Preferences are kept in the slider's accessible description ("Current value 150 percent") and snapped to steps.

Reference: AbCS `src/ui/preview_window.py` (`ListenPositionSlider`, `_ListenPositionSliderAccessible`), `src/ui/web_fetch_progress.py`, `src/ui/preferences_window.py`.

## 41. Low vision, window placement, and platform notes

Low vision (AbCS):
- Focus rings of 2 px `palette(highlight)` on inputs, buttons, spin boxes, sliders, and toolbar toggles; 3 px in high-contrast themes.
- Checkboxes: a highlight border, filled solid when checked, no check glyph.
- High-contrast themes; dark mode read from the Windows registry, because Qt's detection was unreliable; a Mid color derived from base and text so gridlines stay visible on dark themes.
- Zoom and theme each own a marked block of the application stylesheet, so one does not overwrite the other. A widget stylesheet is needed to beat an application-wide `* { font-size }` rule.
- Do not show errors in red text alone.

Window placement:
- Keep windows on screen at high zoom (clamp after layout). Open the main window maximized. Center small dialogs. Size a dialog so its full title is visible.
- A window that must stay above its owner on every show (Listen) calls `SetWindowPos(HWND_TOP)` after setting the Win32 owner.
- A message needed before `QApplication` exists uses a native Win32 `MessageBoxW` with topmost and foreground flags.

Linux (Fusion):
- Use a minimal stylesheet. Do not style `::drop-down` or `::down-arrow`, which breaks Fusion painting. Set `QT_LOGGING_RULES` before `QApplication` to hide harmless painter warnings.
- `AccessibleDialog` has no Linux owner equivalent, so those dialogs are not tied to their owner window there.

Reference: AbCS `src/accessibility/style_helpers.py`, `scaling.py`, `theme_manager.py`, `windows_theme_detector.py`, `linux_qt_compat.py`, `src/main.py`.
