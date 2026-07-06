# PySide6 Screen Reader Accessibility Best Practices

This document is a principles-first reference for designing accessible PySide6 interfaces. Runnable examples live in this repository (`main.py` and helper modules).

## 1. Never rely on visuals alone

If text matters, expose it through accessible widgets and metadata.
- Use `QLabel` for display-only text where possible.
- Use read-only input widgets only when interaction semantics are required.

## 2. Keyboard-first navigation is mandatory

Every major action must be reachable by keyboard.
- Ensure controls are focusable when needed.
- Avoid mouse-only interaction paths.
- Keep tab order explicit and predictable.

## 3. Accessible names and descriptions are required

Always define meaningful names/descriptions for important controls, groups, and dialogs.
- Name: what this control is.
- Description: what this control does or how to use it.

## 4. Status changes must be announced

Do not rely only on `QStatusBar.showMessage()`.
- Mirror status updates to accessibility metadata.
- Provide explicit re-read support (for example `Alt+/`).

## 5. Errors should be foregrounded

When validation fails:
- Use an accessible modal dialog or focused inline error.
- Move focus to the next corrective action.

## 6. Keep action discoverability high

Prefer enabled actions with clear error feedback over silent disabled controls when possible.
- Users can discover available commands.
- Feedback can teach the workflow.

## 7. Avoid global Enter/Return shortcut conflicts

Do not bind global Enter/Return shortcuts that override normal button activation.
- Let focused buttons use native Enter behavior.
- Scope key handling to specific widgets or contexts.

## 8. Use screen reader-friendly help dialogs

For shortcut help and static guidance:
- Use simple list/table structures.
- Keep wording short and explicit.
- Ensure each row has meaningful accessible text.

For long static body text (About, License, Setup):
- Use read-only `QTextEdit` via `create_accessible_read_only_text()` — not `QLabel`.
- Set a short accessible name; put content in the document, not the name.
- Enable `TextSelectableByKeyboard` so arrow keys move line by line.
- Collapse empty lines in source text to avoid JAWS repeating the previous line.

For long plot text in view mode:
- Use `PlotLineList` (one list row per review line; rating on row 0).
- Keep continuous prose in the database and in edit-mode `QTextEdit`.

See implementation reference sections 11–12.

## 9. Reduce table announcement noise

Where row numbers do not help:
- Hide vertical row headers.
- Provide semantic `AccessibleTextRole` values for meaningful cells.

## 10. Treat focus management as part of accessibility

After save/delete/import/cancel operations:
- Restore focus intentionally.
- Keep users in a predictable workflow position.

## 11. Dialog windows must be accessibility roots (Insert+T)

When a dialog opens, screen readers must identify **that dialog** as the current window, not the window behind it.

- Do not use `QDialog(parent=mainWindow)` for feature dialogs — Qt exposes that as an accessibility child of the parent, so JAWS Insert+T reads the parent's title.
- Use `AccessibleDialog` (`styled_dialogs.py` (`AccessibleDialog`)): logical `parent` is passed for Win32 ownership/z-order, but the Qt parent is `None` so the dialog is a root in the MSAA/UIA tree.
- Verify with JAWS Insert+T after opening each major window and after F1 help popups.
- Exception: modeless utility windows with special z-order needs (for example `ImportProgressWindow`) may remain standard `QDialog` with a Qt parent when `AccessibleDialog` would break scan/cancel behavior.

## 12. Test with more than one screen reader

Use at least two screen readers in validation when possible.
- Different engines expose different accessibility gaps.
- Cross-checking catches regressions earlier.

## 13. Keep implementation and principles separate

Documentation model:
- Principles live in this best-practices document.
- Concrete implementation patterns and code references live in the implementation reference document.

## 14. Detect screen readers before speech-only behavior

Do not assume every user wants spoken status updates.
- Detect running screen readers when possible before focus-brief announcements.
- Combine `QAccessible.isActive()` with process detection for reliability.
- Use per-reader timing when restoring focus after status readback.

See implementation reference section 14.

## 15. Initialize accessibility at application startup

Activate Qt accessibility before the first window appears.
- Call `QAccessible.setActive(True)` and `setRootObject(app)` in `main()`.
- Delaying activation can cause missed events on early dialogs.

See implementation reference section 15.

## 16. Announce dialog open and close events

Screen reader users benefit from explicit dialog boundaries.
- Emit dialog start/end accessibility events when feature dialogs open and close.
- Keep dialog titles short and accurate for Insert+T verification.

See implementation reference section 16.

## 17. Separate tooltips from accessible descriptions

Tooltips are for sighted hover help; descriptions are for screen readers.
- Do not let `setToolTip()` replace meaningful `setAccessibleDescription()` text.
- Describe the action or purpose in accessible descriptions, not icon names.

See implementation reference section 17.

## 18. Use accessible message boxes for errors and confirmations

Validation and confirmation dialogs must be readable and actionable.
- Prefer a shared styled message box helper with explicit button labels.
- Return focus to the field or control that needs correction after errors.

See implementation reference section 18.

## 19. Support UI scaling without breaking accessibility

High zoom is an accessibility feature, not just a visual preference.
- Scale fonts, touch targets, and focus indicators together.
- Avoid hover-only cues that do not translate to keyboard or screen reader use.

See implementation reference section 19.

## 20. Provide context-sensitive help architecture

Help should be discoverable and navigable by keyboard.
- F1 for shortcut lists; Shift+F1 for window-specific process help when applicable.
- Help content areas should support arrow-key line review and predictable Tab cycles.

See implementation reference section 20.

## 21. Announce meaningful selection changes

Selection state should be available in status or accessible text, not only visually.
- Announce concise selection summaries for primary lists and tables.
- Use semantic accessible text roles on rows and cells.

See implementation reference section 21.

## 22. Let Tab exit large tables

Tab should move through the workflow, not every table cell.
- Tab and Shift+Tab should leave the table to the next logical control.
- Define explicit tab order around tables.

See implementation reference section 22.
