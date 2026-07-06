# PySide6 Accessibility Patterns and Implementation Reference

This document is the code-oriented reference for accessibility patterns demonstrated in this repository's sample application.

Runnable sample files (repository root):
- `accessibility_patterns.py` — core helpers and `AccessibilityMixin`
- `main.py` — main demo window exercising all patterns
- `styled_dialogs.py` — `AccessibleDialog` and message box helpers

## Scope

Use this document when implementing or refactoring windows, dialogs, forms, and tables in PySide6 applications.

## 1. Status announcement pattern

Goal: make status updates reliably available to screen reader users.

Pattern:
- Provide a per-window status API (for example `set_status(...)`).
- Keep a default status message for explicit readback.
- Support `Alt+/` to re-read the current status on demand.
- Announce only meaningful state changes.

Reference files:
- `accessibility_patterns.py`
- `main.py`
- `main.py`
- `main.py`

## 2. Editable combo anti-noise pattern

Goal: prevent silent value changes and accidental edits.

Pattern:
- Install event filters on editable combos and their line edits.
- Block plain Up/Down keys when they can silently change values (events may arrive on the combo **or** its internal `lineEdit()`).
- Allow explicit dropdown actions with Alt+Down / Alt+Up (`showPopup()`).
- Use beep or equivalent feedback when blocking key input.
- When combining `AccessibilityMixin` with `QDialog` subclasses, list **`AccessibilityMixin` before the dialog base class** in the class definition. Otherwise Qt's built-in `QObject.eventFilter` shadows the mixin's Python `eventFilter` and combo blocking will not run.

Reference files:
- `accessibility_patterns.py`
- `main.py`

## 3. Alt-key hygiene pattern

Goal: avoid stray Alt+letter input leaking into text fields.

Pattern:
- Define a per-window allowlist of Alt+letter actions.
- Consume unmapped Alt+letter events in event filters.
- Keep `Alt+/` available in major windows.

Reference files:
- `accessibility_patterns.py`
- `main.py`
- `main.py`

## 4. AccessibleDialog window title pattern (JAWS Insert+T)

Goal: ensure screen readers read the **active dialog title**, not the window behind it.

### Problem

Qt's MSAA/UIA bridge exposes `QDialog(parent=X)` as an accessibility **child** of `X`. JAWS Insert+T walks up the tree from the focused control:

`focused_control → … → DialogWindow → MainWindow`

and reads `MainWindow`'s title instead of the dialog's (for example "Book Details").

### Solution: `AccessibleDialog`

All feature dialogs and inline help/popup dialogs inherit from `AccessibleDialog` (`styled_dialogs.py`) instead of `QDialog` directly.

Pattern:
- Pass the logical owner as `parent` to `AccessibleDialog.__init__(parent)` — the base class stores it but calls `QDialog.__init__(None)` so the dialog is a **root** in the accessibility tree.
- On Windows, set the Win32 **owner** via `SetWindowLongPtrW(GWL_HWNDPARENT)` so taskbar grouping and z-order still follow the calling window, without creating an accessibility parent chain.
- On `showEvent`, re-fire focus after 300 ms so JAWS registers the new window before Insert+T is used (subclasses that override `showEvent` must call `super().showEvent(event)`).
- Subclasses that override `done()` must call `super().done(r)`.
- When a window also uses `AccessibilityMixin`, inherit as `class MyWindow(AccessibilityMixin, AccessibleDialog)` so `eventFilter` and dialog-root behavior both apply (see section 2 MRO note).

**Feature window example:**
```python
from styled_dialogs import AccessibleDialog

class InfoDialog(AccessibleDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="Sample Info Dialog")
        # ...
```

**Inline F1 / popup example:**
```python
dlg = AccessibleDialog(self)
dlg.setWindowTitle("Keyboard Shortcuts - Book Details")
dlg.exec()
```

### Exception: `ImportProgressWindow`

`ImportProgressWindow` remains a standard `QDialog` with a normal Qt parent (`parent=self` on `ImportWindow`). It is a modeless scan utility that must stay above its owner via Qt z-order and handle Escape/cancel during an active scan. Do **not** migrate it to `AccessibleDialog`.

Modeless utility windows that do use `AccessibleDialog` may set `self._announce_focus_on_show = False` in `__init__` to skip the 300 ms focus refire when repeated `show()` calls would steal focus.

Reference files:
- `styled_dialogs.py`
- `main.py`
- `main.py` (Find, Duplicate Check, ReadDateDialog, F1 help)
- `main.py` (intentional `QDialog` exception)

## 5. Modal dialog accessibility pattern

Goal: make warnings/confirmations readable and actionable.

Pattern:
- Use a consistent modal helper where possible.
- Set clear dialog title/text and explicit button labels.
- Set accessible name and description for custom dialogs.
- Return focus to the most relevant control after dialog close.
- Use `AccessibleDialog` for custom modal dialogs (see section 4), not raw `QDialog(parent)`.

Reference files:
- `accessibility_patterns.py`, `styled_dialogs.py`
- `main.py`
- `main.py`
- `styled_dialogs.py`

## 6. Keyboard shortcut implementation pattern

Goal: prevent conflicts and keep shortcut behavior predictable.

Pattern:
- Keep `F1`, `Escape`, and `Alt+/` as local window shortcuts.
- Register Alt+field shortcuts through centralized shortcut maps.
- Use lambda callbacks for mapped actions when needed.

Reference files:
- `main.py`
- `main.py`
- `main.py`

## 7. Accessible help dialog pattern (F1)

Goal: provide a stable and readable shortcut list.

Pattern:
- Use a simple one-column read-only table or list.
- Provide per-row accessible text with explicit key + action wording.
- Include `Alt+/` in each window help list.
- Instantiate help with `AccessibleDialog(self)`, not `QDialog(self)` (see section 4).

Reference files:
- `main.py`
- `main.py`
- `main.py`

## 8. Focus safety pattern for editable fields

Goal: reduce accidental full-value overwrite.

Pattern:
- On FocusIn, defer deselect/cursor behavior with `QTimer.singleShot(0, ...)`.
- Deselect auto-selected text in line edits and combo line edits.

Reference files:
- `main.py`
- `main.py`
- `main.py`

## 9. Table accessibility pattern

Goal: improve data comprehension in row-based widgets.

Pattern:
- Hide row-number headers when they add no meaning.
- Add semantic text via `Qt.AccessibleTextRole` for key cells.

Reference files:
- `main.py`
- `main.py`
- `main.py`

## 10. About/Info Dialog Pattern

Goal: Provide a consistent, accessible, and themed approach for About, License, Setup, and other informational dialogs.

Pattern:
- Use external dialog classes (e.g., `AboutDialog`, `LicenseDialog`, `SetupDialog`) instead of inline popups in main windows.
- Inherit from `AccessibleDialog`, not `QDialog` (see section 4).
- Structure dialog with header/content/footer using `QVBoxLayout`.
- **Use `create_accessible_read_only_text()` for body text** — not `QLabel` (see section 11).
- Footer: right-aligned, styled OK/Close button using `build_accessible_button_style()`.
- Apply font scaling with `scaler.get_scaled_size()` for all text and controls.
- Set a **short** accessible name and a helpful accessible description on the text area.
- Ensure dialog is modal and returns focus to main window after closing.
- Test with JAWS/NVDA for screen reader feedback (verify Insert+T reads the dialog title).

Example usage in main window:
```python
from main import InfoDialog

def on_open_info_dialog(self):
    dlg = InfoDialog(self)
    dlg.exec()
    self.info_button.setFocus()
```

Reference files:
- `styled_dialogs.py`
- `main.py (`InfoDialog`)`
- `main.py (`InfoDialog`)`
- `main.py (`InfoDialog`)`
- `accessibility_patterns.py`
- `accessibility_patterns.py`, `styled_dialogs.py`

## 11. Read-only navigable text pattern

Goal: let JAWS/NVDA users move through static help or license text line by line with arrow keys.

### Problem

`QLabel` with the full body in `setAccessibleName()` causes the screen reader to dump all text at once. Arrow keys do not move line by line. Empty lines in the source text can also cause JAWS to repeat the previous line.

### Solution: `create_accessible_read_only_text()`

Module: `accessibility_patterns.py`

Use a read-only `QTextEdit` configured for keyboard review:

```python
from accessibility_patterns import create_accessible_read_only_text

about_label = create_accessible_read_only_text(
    self,
    about_text,
    "About information",  # short name only — not the full body
    "About AbCS. Use arrow keys to read line by line. Press Tab to move to OK button.",
)
about_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
```

`configure_accessible_read_only_text()` applies these settings:
- `setReadOnly(True)`
- `setTextInteractionFlags(Qt.TextSelectableByKeyboard)` — enables arrow-key line review
- `setFocusPolicy(Qt.StrongFocus)` and `setTabChangesFocus(True)`
- `setMouseTracking(False)` on widget and viewport; `WA_Hover` disabled
- Transparent background / no frame for dialog embedding
- Body text passed through `_collapse_blank_lines()` to remove empty lines that confuse JAWS

### Rules

- **Never** put the full body text in `setAccessibleName()`.
- Use a short accessible name (for example `"License information"`) and a brief description that mentions arrow-key review.
- Decorative graphics (splash image) use `Qt.NoFocus`.
- Set initial focus to the text area with `QTimer.singleShot(100, lambda: text_widget.setFocus(Qt.TabFocusReason))`.

### Where used

- `main.py (`InfoDialog`)`
- `main.py (`InfoDialog`)`
- `main.py (`InfoDialog`)`

## 12. Plot field line-by-line review pattern

Goal: let screen reader users review plot text line by line in view mode while keeping continuous prose in the database and edit mode.

### Problem

- Read-only `QTextEdit` did not give reliable Up/Down line navigation in JAWS/NVDA.
- Putting the full plot in `setAccessibleName()` made review worse.
- Splitting every sentence into list rows looked like blank lines between items and polluted stored text with extra line breaks.

### Solution: `PlotLineList` + edit `QTextEdit`

Module: `accessibility_patterns.py`

**View mode (read-only review):** `PlotLineList` — a `QListWidget` subclass with one row per navigable line.

**Edit mode:** standard `QTextEdit` loaded with `set_navigable_plain_text()` (continuous prose, no injected breaks).

**Book Details** stacks both in a `QStackedWidget`:
- View: `plot_review` (`PlotLineList`)
- Edit: `comments_edit` (`QTextEdit`)
- Switch widgets in `_set_fields_read_only()`; sync prose with `format_plot_text_for_navigation()` when returning to view mode.

**Web Metadata** uses `PlotLineList` for the plot field.

### How plot rows are built

`plot_lines_for_review()` loads text into the list:
1. **Item 0:** rating line only (for example `Rating: 3.5 (2 ratings)`), when present.
2. **Items 1+:** plot body split into lines of at most **73 characters**, breaking only at word boundaries (`_wrap_at_words()`).

Storage and edit mode use `format_plot_text_for_navigation()` — normalizes line endings, rejoins legacy sentence-per-line data, and keeps plot body as continuous prose. **Do not** inject sentence line breaks into stored text.

Compare plot text with `plot_text_equivalent()` (ignores line-break and whitespace differences).

### PlotLineList accessibility and visual settings

- `setAccessibleName("Plot")` — short label only; row text comes from `AccessibleTextRole` per item.
- `setAccessibleDescription("")` — avoid duplicate announcements.
- `setSpacing(0)`, `setUniformItemSizes(True)`, zero item padding in stylesheet.
- `_CompactPlotLineDelegate` paints single-line rows at `fontMetrics().height()` so rows stack tightly without visual gaps.
- Selected/focused rows use base background (no highlight bar) so the field does not flash a selection color while reviewing.
- `setMouseTracking(False)`; `WA_Hover` disabled on widget and viewport.

Example:
```python
from accessibility_patterns import PlotLineList

self.plot_review = PlotLineList()
self.plot_review.setAccessibleName("Plot")
self.plot_review.set_plot_text(self.book.comments or "")
```

### Rules

- Use `PlotLineList.set_plot_text()` to load; do not call `setPlainText()`.
- Keep rating on its own list row (item 0), separate from plot body lines.
- Do not break words when wrapping plot lines for the list.
- Do not put full plot text in `setAccessibleName()`.
- Web metadata save path: `_build_plot_text_for_db()` uses `format_plot_text_for_navigation()`, not sentence splitting.

Reference files:
- `accessibility_patterns.py`
- `main.py`
- `main.py (`PlotLineList` tab)`
- add unit tests in your project

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
- Use per-reader focus-restore delay values when briefly moving focus to the status bar (JAWS ~300 ms, NVDA ~1500 ms, Narrator ~3500 ms, Orca ~800 ms).

Reference files:
- `accessibility_patterns.py`
- `accessibility_patterns.py`

## 15. QAccessible initialization pattern

Goal: ensure Qt's accessibility bridge is active before windows open.

Pattern:
- Call `QAccessible.setActive(True)` at application startup.
- Call `QAccessible.setRootObject(app)` so the application object is the accessibility root.
- Run this once in `main()` before creating the primary window.

Reference files:
- `main.py`

## 16. Dialog lifecycle event pattern

Goal: notify screen readers when modal or feature dialogs open and close.

Pattern:
- On dialog open, call `announce_dialog_opened(dialog, title)` to emit `QAccessible.Event.DialogStart`.
- On dialog close, call `announce_dialog_closed(dialog)` to emit `QAccessible.Event.DialogEnd`.
- Set a short accessible name on the dialog when a title is provided.
- Only emit events when `QAccessible.isActive()` is true.

Reference files:
- `accessibility_patterns.py`
- `main.py`
- `main.py (`PlotLineList` tab)`

## 17. Tooltip vs accessible description pattern

Goal: give sighted users tooltips without overwriting screen reader descriptions.

Pattern:
- Set `setToolTip(tooltip)` for sighted hover text.
- Set `setAccessibleDescription(description)` separately for screen reader guidance.
- Use `apply_tooltip_accessibility(widget, tooltip, description)` so tooltips never replace existing accessible descriptions.
- For menu/toolbar actions, keep decorative icons out of accessible names.

Reference files:
- `accessibility_patterns.py`, `styled_dialogs.py`
- `main.py`

## 18. Styled message box pattern

Goal: make validation and confirmation dialogs readable and keyboard-safe.

Pattern:
- Use `exec_styled_message_box(parent, ...)` instead of raw `QMessageBox` where theming and accessibility matter.
- Set accessible names and descriptions on message box buttons.
- Use decorative standard icons without putting icon text into spoken names.
- Return focus to the corrective control after validation failures.

Reference files:
- `accessibility_patterns.py`, `styled_dialogs.py`
- `main.py`
- `main.py`

## 19. UI scaling pattern

Goal: keep controls readable at high zoom without breaking focus or table semantics.

Pattern:
- Centralize zoom in a scaler (for example 50–300%, default 150%).
- Scale fonts, button heights, combo heights, and status bar font together.
- Apply table/combo CSS that disables hover noise and keeps focus borders visible.
- On Linux, prefer minimal stylesheets when platform painting is fragile.

Reference files:
- `styled_dialogs.py` (font sizing); production apps may add a dedicated scaler module
- `styled_dialogs.py`
- platform-specific production code

## 20. Help system architecture pattern

Goal: provide discoverable, context-sensitive help without accessibility noise.

Pattern:
- Discover markdown help topics at runtime from a `help_docs/` folder.
- Route **Shift+F1** per window via a `WINDOW_HELP_MAP` (context-sensitive process help).
- Use **F1** for per-window shortcut tables (simple read-only list/table).
- In the Help window, use a nav list plus content area with an explicit Tab cycle between nav and body.
- Keep Help-window zoom independent of global UI zoom; default Help zoom to 100% when a screen reader is active.

Reference files:
- `main.py` (Shift+F1 stub)
- `main.py`
- `main.py`
- `main.py`

## 21. Selection announcement pattern

Goal: make list/table selection changes meaningful without relying on visual highlighting alone.

Pattern:
- On selection change, build a concise status message (for example title, optional "plot" hint, shortcut reminder).
- Call `set_status(message, announce=True)` only for meaningful selection changes.
- Put semantic cell/row text in `Qt.AccessibleTextRole`, not only in display text.

Reference files:
- `main.py`
- `main.py`

## 22. Tab-exits-table pattern

Goal: prevent Tab from trapping users inside large tables.

Pattern:
- Replace or wrap the table's `keyPressEvent` so **Tab** and **Shift+Tab** move focus to the next/previous widget in the tab chain.
- Delegate all other keys to the default `QTableWidget.keyPressEvent`.
- Pair with explicit `setTabOrder` so the exit target is predictable.

Reference files:
- `main.py`
- `main.py`
- `main.py`
