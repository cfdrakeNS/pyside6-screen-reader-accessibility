# PySide6 Screen Reader Accessibility Best Practices

This document is a principles-first reference for designing accessible PySide6 interfaces. Code patterns are in [PySide6_Accessibility_Patterns_and_Implementation_Reference.md](PySide6_Accessibility_Patterns_and_Implementation_Reference.md) (the implementation reference), and runnable examples are in this repository (`main.py` and helper modules). The mapping to the AbCS standards is in [AbCS_Standards_Crosswalk.md](AbCS_Standards_Crosswalk.md).

## 1. Never rely on visuals alone

If text matters, expose it through accessible widgets and metadata.
- Use `QLabel` for short display-only text.
- Use read-only text widgets when the user must review the text line by line (principle 8).

## 2. Keyboard-first navigation is mandatory

Every major action must be reachable by keyboard.
- Ensure controls are focusable when needed.
- Avoid mouse-only interaction paths.
- Keep tab order explicit and predictable.

## 3. Accessible names and descriptions are required

Always define meaningful names and descriptions for important controls, groups, and dialogs.
- Name: what this control is.
- Description: what this control does or how to use it.
- Keep names and descriptions on dialogs too; do not clear them to reduce speech.
- `QAction` menu items are named by their menu text; do not set an accessible name on them.
- An image that carries information takes focus and has a spoken name; a decorative image does not take focus.

## 4. Status changes must be announced

Do not rely only on `QStatusBar.showMessage()`.
- Announce meaningful changes, such as save, delete, or a validation failure.
- Provide explicit re-read support (for example `Alt+/`).
- Never announce from a hidden window. The announcement lands on the window behind it, and the screen reader reads that window's title instead (principle 23).
- Keep shortcut hints out of status messages. Put them in accessible descriptions and the F1 list. The exception is "Press Escape to cancel" or "Esc to close" during a long operation.

## 5. Errors should be foregrounded

When validation fails:
- Use an accessible message box or a focused inline error.
- Include the text the user entered in the message, and keep it in the field so it can be corrected.
- Move focus to the control that needs correcting.

## 6. Keep action discoverability high

Prefer enabled actions with clear error feedback over silent disabled controls when possible.
- Users can discover available commands.
- Feedback can teach the workflow.

## 7. Avoid global Enter/Return shortcut conflicts

Do not bind global Enter/Return shortcuts that override normal button activation.
- In a dialog with one clear main action, make it the default button so Enter runs it.
- In a form with several buttons, turn the default off on every button and let Enter click the button that has focus.
- Scope key handling to specific widgets or contexts.

See implementation reference section 5.

## 8. Make static text reviewable line by line

For shortcut help:
- Use a simple one-column list or table in its own dialog.
- Keep wording short and explicit, with meaningful accessible text on each row.

For About, License, Setup, and info text:
- Use a read-only text area, not a `QLabel`. Give it a short accessible name; put the content in the document, not the name.
- Short instructions (1 to 3 sentences) are the exception: a focusable label may carry its whole text as its name, so it is read at once.
- Make each heading, line, and list item its own paragraph.
- Do not let paragraphs wrap. JAWS reads each wrapped line as you arrow, then rereads the whole paragraph. Keep sentences short and size the dialog to fit the longest one.
- Remove empty lines, which can make JAWS repeat the previous line.

For long prose in view mode (for example a book plot):
- Use one list row per review line, with the rating on its own first row.
- Keep continuous prose in storage and in the edit field.

See implementation reference sections 7, 11, and 12.

## 9. Tables must read content, not coordinates

- Give every cell spoken text, and leave no cell empty. An empty cell or a cell without accessible text makes JAWS read its coordinates.
- In a label/value table, make each cell speak "label: value", so either cell reads the whole row.
- Silence row headers completely. Hiding them is not enough; also disable them and label them empty.
- Make the selection easy to see: a solid highlight that stays visible when the table loses focus.
- Do not announce on every arrow key (principle 21).

See implementation reference section 9.

## 10. Treat focus management as part of accessibility

After save, delete, import, cancel, or any dialog or message box:
- Restore focus intentionally.
- Keep users in a predictable workflow position.
- After No on an unsaved-changes prompt, return to the field the user was editing.

See implementation reference section 24.

## 11. Dialog windows must be accessibility roots (Insert+T)

When a dialog opens, screen readers must identify **that dialog** as the current window, not the window behind it.

- Do not use `QDialog(parent=mainWindow)` for feature dialogs. Qt exposes it as an accessibility child of the parent, so JAWS Insert+T reads the parent's title.
- Use `AccessibleDialog` (`styled_dialogs.py`). The logical parent is used for Win32 ownership and z-order, but the Qt parent is `None`, so the dialog is a root in the MSAA/UIA tree.
- Verify with JAWS Insert+T after opening each major window and each F1 help popup.
- With focus in a text field, the read-dialog command reads the title and that field. Put the dialog's instructions in the field's accessible description, or start focus on a button or combo when the whole dialog must be read.
- Exception: modeless utility windows with special z-order needs (for example AbCS `ImportProgressWindow`) may stay a standard `QDialog` with a Qt parent when `AccessibleDialog` would break their behavior.

See implementation reference section 4.

## 12. Test with more than one screen reader

Use at least two screen readers in validation when possible.
- Different engines expose different accessibility gaps.
- Cross-checking catches regressions earlier.

See principle 26 for the checklist.

## 13. Keep implementation and principles separate

Documentation model:
- Principles live in this best-practices document.
- Concrete implementation patterns and code references live in the implementation reference.

## 14. Detect screen readers before speech-only behavior

Do not assume every user wants spoken status updates.
- `QAccessible.isActive()` alone is not a screen reader test; Magnifier and the touch keyboard also turn it on.
- Change the interface (typed fields, hidden visual content) only when a screen reader process is running.
- Allow announcements when either check is true, so speech still works with an unknown reader.
- Use per-reader timing when restoring focus after status readback.

See implementation reference section 14.

## 15. Initialize accessibility at application startup

Activate Qt accessibility before the first window appears.
- Call `QAccessible.setActive(True)` and `setRootObject(app)` in `main()`.
- Delaying activation can cause missed events on early dialogs.

See implementation reference section 15.

## 16. Announce dialog open and close events

Screen reader users benefit from explicit dialog boundaries.
- Emit dialog start and end accessibility events when feature dialogs open and close.
- Emit the start event once the dialog is shown, not before.
- Keep dialog titles short and accurate for Insert+T verification.
- Speech of the window behind a dialog, when the dialog closes, is expected. Treat it as a bug only when that speech cuts off a message the user still needs, or when focus goes to the wrong window.

See implementation reference section 16.

## 17. Separate tooltips from accessible descriptions

Tooltips are for sighted hover help; descriptions are for screen readers.
- Do not let `setToolTip()` replace meaningful `setAccessibleDescription()` text.
- Describe the action or purpose in accessible descriptions, not icon names.

See implementation reference section 17.

## 18. Use accessible message boxes for errors and confirmations

Validation and confirmation boxes must be readable and actionable.
- Use a shared styled message box helper with explicit, named buttons.
- A message box over a dialog must not disable that dialog. Otherwise JAWS says "<title> unavailable" before reading the box.
- A box that opens just after another dialog closes must wait until a visible window is active. Otherwise the screen reader reads the window behind the box.
- Escape answers Cancel, or No when the message has no Cancel. Escape and the window's close box both run the unsaved-changes check.
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

## 21. Announce selection only when the user selects

Selection state should be available in status or accessible text, not only visually, without adding noise.
- While the user arrows through a table or list, let the cell's accessible text speak. Do not also announce through the status bar.
- Announce after explicit selection actions, such as multi-select ("3 selected").
- Keep the status text current so Alt+/ can read it.
- Exception: when Up/Down changes a focused value field (a year or date), speak the new value.

See implementation reference section 21.

## 22. Let Tab exit large tables

Tab should move through the workflow, not every table cell.
- Tab and Shift+Tab should leave the table to the next logical control.
- If that next control is hidden, keep focus on the current cell.
- Define explicit tab order around tables.

See implementation reference section 22.

## 23. Open windows quietly and predictably

When a window opens, the screen reader should speak only that window.
- Set starting values in the constructor, before the window is shown.
- Set first focus after the window is shown, not in the constructor.
- Announce nothing while the window is hidden.
- When a menu item opens a window, keep focus off the window behind it until the new window is shown.

See implementation reference sections 23 and 26.

## 24. Choose controls that read back reliably

Some controls are noisy or change value silently with a screen reader.
- A spin box speaks every Up/Down step and can change its value while the user reviews it. When a screen reader is running, use a typed text field with a placeholder and validate on save.
- Keep the familiar control for sighted users when it works well for them.

See implementation reference section 25.

## 25. Keep the interface responsive and stable during background work

- Show and focus a progress window before disabling the controls that started the work. If a confirm box just closed, let that window finish becoming active first. The progress window is the next thing spoken.
- When background work finishes, bring the window forward and focus its main button before announcing.
- Never update widgets from a worker thread.

See implementation reference sections 28 and 39.

## 26. Testing gate

Before marking a UI change done:
1. Tab through every new control; each speaks a useful name and, where it has one, a value.
2. Activate the primary action and Cancel/Close with the keyboard only.
3. Alt+/ reads the latest status after a meaningful action.
4. Focus returns to a sensible place after each dialog or message box closes.
5. Insert+T reads the new window's title, and only the new window is spoken when it opens.
6. A box over a dialog is not preceded by "<title> unavailable".
7. Tables read cell content, not coordinates or row numbers.
8. Dialog text reads each line once, with no repeated wrapped lines.
9. Up or Down on a year or date field speaks the new value. Arrowing a table or list does not announce that move.
10. An unavailable action says why. Escape and the close box both run the unsaved-changes check.

See implementation reference section 29.

## 27. Re-read what changed under the user's focus

When content changes but focus does not move (the next record loads into the same window, a help topic loads), the screen reader stays silent. Make it read the new content once, and keep names and descriptions in step with the control's state.

See implementation reference section 30.

## 28. Validate without false alarms

Leaving a field should be the only thing that triggers its focus-out check.
- An announcement or a message box taking focus is not leaving the field.
- Filling a form from code must not mark it changed, announce, or validate.
- Show one warning per problem.

See implementation reference section 31.

## 29. No silent value changes

- Block the mouse wheel and plain Up/Down on value controls where they could change a value unnoticed.
- A read-only control stays focusable and says it is read-only.
- Never show a placeholder date such as 1752-09-14; a blank date reads as blank.

See implementation reference sections 32 and 33.

## 30. Tab reaches what is visible, and only that

- Rebuild the Tab order when controls appear or disappear.
- No empty Tab stops (scroll areas, window frames).
- Fix the order by hand where Qt or the screen reader skips controls.

See implementation reference section 34.

## 31. Unavailable commands stay findable

- Keep disabled menu items reachable with the arrow keys, so they are read as unavailable.
- Prefer enabled buttons that explain what is missing over disabled buttons that drop out of the Tab order.
- A shortcut or button that cannot act says why.

See implementation reference section 35.

## 32. Keep the user's place in lists

- After a reload, sort, or delete, focus stays on the same record or moves to its neighbor.
- Large selections stay fast.
- Find and filter never trap focus; Escape always returns to the list.

See implementation reference sections 36 and 37.

## 33. Long operations speak once, and end where they started

- The progress window is the next thing spoken when work starts.
- Each step is spoken once.
- The progress window stays open with the summary when work ends, and Escape closes it.

See implementation reference section 39.

## 34. Give meaningless values a meaningful voice

When a control's default spoken value is useless (a slider's raw seconds), provide a custom accessible interface. Send change events for user actions, not for automatic updates, and pause any audio before a prompt.

See implementation reference section 40.
