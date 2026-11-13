# AbCS Standards Crosswalk

This page maps each rule in the AbCS accessibility standard to the matching section of this repository's [implementation reference](PySide6_Accessibility_Patterns_and_Implementation_Reference.md) (IR) and to the demo code that shows it.

Source standard: [AbCS `doc/standards/accessibility_ui_standards.md`](https://github.com/cfdrakeNS/AbCS_Audiobook_Collector_Scanner/blob/main/doc/standards/accessibility_ui_standards.md). Shortcut policy: [`standard_shortcuts.md`](https://github.com/cfdrakeNS/AbCS_Audiobook_Collector_Scanner/blob/main/doc/standards/standard_shortcuts.md) and [`shortcut_centralization_status.md`](https://github.com/cfdrakeNS/AbCS_Audiobook_Collector_Scanner/blob/main/doc/standards/shortcut_centralization_status.md).

"AbCS only" means the rule depends on AbCS infrastructure (scaling, icons, menus, background work). The IR describes the principle, but the demo does not implement it.

## Screen reader rules

| AbCS rule | IR section | Demo location |
|---|---|---|
| Dialogs subclass `AccessibleDialog` | 4 | `styled_dialogs.AccessibleDialog`; `InfoDialog`, `AccessibleSampleWindow` |
| Accessible name and description on the dialog and every control | 5 | All controls in `main.py` |
| No `setAccessibleName` on `QAction` | 27 | Documented only (no menus in the demo) |
| Meaningful changes use `set_status(..., announce=True)` | 1 | `AccessibilityMixin.set_status`; `on_save`, `on_delete` |
| Alt+/ re-reads status in every major window | 1, 6 | `AccessibleSampleWindow.setup_shortcuts` |
| Restore focus intentionally after a modal closes | 24 | `on_open_info_dialog`, `on_save`, `InfoDialog.on_test_message_box` |
| Window open: constructor state, first focus in `showEvent`, no announce while hidden | 23 | `AccessibleSampleWindow.showEvent`, `InfoDialog.showEvent`, `set_status` visibility check |
| Menu items that open windows hold focus on the menu bar | 26 | AbCS only |
| Message boxes over dialogs use `exec_styled_message_box` (no "unavailable") | 18 | `exec_styled_message_box`; `InfoDialog` Test message box button |
| A box that opens just after a dialog closes waits until a visible window is active | 18 | `_settle_owner_activation` in `exec_styled_message_box` (same name as AbCS) |
| Escape answers Cancel, or No when the message has no Cancel. Escape and the close box both run the unsaved-changes check | 18 | AbCS `escape_only_button`. Not in the demo |
| A small dialog that must be read whole with Insert+B has no text fields; dates use Year, Month, and Day combo boxes | 5 | `DateComboFields`, `ReadDateDialog` (Alt+R). AbCS read date and Recently Added use `src/accessibility/date_combo_fields.py` |
| Tab stays on the current cell when the next control is hidden | 22 | AbCS main table when no footer button is showing |
| Speech of the window behind a dialog, when the dialog closes, is expected | 16 | Documented. AbCS follows this; Web Metadata stores `saved_message` |
| Show and focus a progress window before disabling the caller's buttons | 28, 39 | AbCS only |
| Modal completion: raise, activate, focus default button, then announce | 28 | AbCS only |
| Worker threads update the UI only through a GUI-thread `QObject` bridge | 28 | AbCS only |
| Block unmapped Alt+letter; editable combos block plain Up/Down | 2, 3 | `AccessibilityMixin.eventFilter`; `category_combo` |
| No global Enter/Return shortcuts | 6 | No Enter shortcuts in `setup_shortcuts` |
| F1 shortcuts, Shift+F1 process help, help docs | 7, 20 | `exec_shortcuts_dialog`; `on_context_help` (stub) |

## Buttons, footers, and control formatting

| AbCS rule | IR section | Demo location |
|---|---|---|
| Buttons use `build_accessible_button_style` with `UIScaler` heights | 10, 19 | AbCS only (demo uses default buttons) |
| Main-window footer buttons follow `update_selection_ui()` rules | — | AbCS only (app-specific) |
| Default button only on a dialog with one clear main action; forms turn defaults off and Enter clicks the focused button | 5 | `InfoDialog.close_button` (default); `AccessibleSampleWindow.keyPressEvent` (form) |
| Decorative icons only through `apply_decorative_action_icon` | 17 | AbCS only |
| Combos use `build_accessible_combo_box_style`; anti-noise filter when editable | 2 | Filter in demo; styling AbCS only |
| Checkboxes use `build_accessible_checkbox_style` | — | AbCS only |
| Message boxes are styled (scaled font, app icon) | 18 | Demo uses system font and no app icon |
| Respect `UIScaler` and theme; no hard-coded sizes | 19 | AbCS only |
| Tooltips paired with screen reader descriptions | 17 | `apply_tooltip_accessibility` |

## Per-change gate

The AbCS JAWS smoke gate is IR section 29. Items 1–6 match. Items 7–8 (table content, dialog lines read once) were added from this demo and are now in the AbCS gate. Items 9–10 (a stepped value speaks, and Escape runs the same unsaved-changes check as the close box) come from the November 2026 AbCS retest.

## Cross-cutting principles

AbCS cross-cutting principles 1–4 (tests, `pytest`, test logic first, tests in the same commit) apply to AbCS development. This repository has no automated tests yet; the manual gate in IR section 29 is the check.

## Patterns in this reference that the AbCS standard does not list yet

The November 2026 AbCS standard now includes the items this table used to hold: cell accessible text, no status announce while arrowing a table, dialog prose that does not wrap, the typed year field, and reactivating the owner after a message box.

These remain in the IR and are still not named in the AbCS standard.

| Pattern | IR section | In AbCS code |
|---|---|---|
| Solid table selection highlight while the table has focus | 9 | Yes (table stylesheet) |
| Selection stays the same color after the table loses focus | 9 | No, and not needed: the November 2026 retest found the AbCS row stays highlighted |
| Status announce falls back to the window's focus widget when the application focus widget is empty | 24 | No, and not needed: the retest found focus returns to the field, because AbCS sets it directly |

IR sections 30–41 describe further AbCS production patterns found in a code audit of every AbCS accessibility workaround: re-reading changed content, focus-out guards, date and stepped-value fields, read-only and noisy controls, dynamic Tab order, findable unavailable commands, records and selections, find and filter, tabbed windows, long operations, custom accessible interfaces, and low vision and platform notes. The AbCS standard covers some of them in its "Confirmed in testing" list; the rest are documented only in the IR. Several AbCS windows do not yet follow the default-button, first-focus, shortcut-hint, and single Alt-beep rules; the AbCS standard lists these as not yet on every window.

## Shortcut policy: what to copy

Copy into any PySide6 application:
- **F1**, **Shift+F1**, **Escape**, and **Alt+/** are local `QShortcut`s on every window.
- **Ctrl+S** saves everywhere.
- Keep each window's allowed Alt+letter list in sync with its shortcuts.
- No global Enter/Return shortcuts.

AbCS-specific (do not copy as-is): the full shortcut matrix in `standard_shortcuts.md`, the ShortcutManager registration, and the centralization phases in `shortcut_centralization_status.md`.

## Maintenance rule

When AbCS `doc/standards` changes, update this crosswalk and the affected IR sections in the same change. When a pattern is added or changed here, update the AbCS standard, or add it to the "does not list yet" table above.
