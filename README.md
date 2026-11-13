# pyside6-screen-reader-accessibility

Screen reader accessibility patterns for PySide6 desktop apps, tested with JAWS, NVDA, Narrator, and Orca. A runnable demo plus copy-paste helpers and documentation. The patterns also apply to PyQt6.

**Repository:** https://github.com/cfdrakeNS/pyside6-screen-reader-accessibility

Formerly `pyside6-accessible-ui-reference`. Old GitHub links redirect here.

## Purpose

- Runnable demo of accessibility patterns documented in `doc/PySide6_*.md`
- Self-contained — no application framework dependencies
- Copy `accessibility_patterns.py` and `styled_dialogs.py` into your own PySide6 projects

## Relationship to AbCS

This project was extracted from [AbCS](https://github.com/cfdrakeNS/AbCS_Audiobook_Collector_Scanner) (Audiobook Collector Scanner). AbCS implements these patterns in production under `src/accessibility/` and `src/ui/` but does not bundle this repository.

- [AbCS accessibility standard](https://github.com/cfdrakeNS/AbCS_Audiobook_Collector_Scanner/blob/main/doc/standards/accessibility_ui_standards.md) — the rules AbCS follows for every UI change
- [AbCS Standards Crosswalk](doc/AbCS_Standards_Crosswalk.md) — maps each AbCS rule to a section of the implementation reference and to the demo code

AbCS adds infrastructure this demo leaves out: UI scaling (`UIScaler`), styled buttons (`build_accessible_button_style`), icons, a help router, and menus. You do not need them to adopt the patterns here.

## Install and run

```bash
git clone https://github.com/cfdrakeNS/pyside6-screen-reader-accessibility.git
cd pyside6-screen-reader-accessibility
pip install -r requirements.txt
python main.py
```

`psutil` is used for screen reader process detection on Windows; it is optional on Linux (detection falls back to `QAccessible.isActive()`).

## Repository layout

| File | Role |
|------|------|
| `main.py` | Demo window (`AccessibleSampleWindow`, `InfoDialog`, `ReadDateDialog`) |
| `accessibility_patterns.py` | `AccessibilityMixin` and helper functions |
| `styled_dialogs.py` | `AccessibleDialog`, F1 shortcut dialog, and styled message boxes |
| `doc/PySide6_Accessibility_Patterns_and_Implementation_Reference.md` | Code patterns (section numbers below) |
| `doc/PySide6_Screen_Reader_Accessibility_Best_Practices.md` | Design principles |
| `doc/AbCS_Standards_Crosswalk.md` | AbCS standard rule to section and demo code |

## Patterns demonstrated

| § | Pattern | Location |
|---|---------|----------|
| 1 | Status bar announce and Alt+/ readback | `announce_status_message`, `AccessibilityMixin.set_status` |
| 2 | Editable combo anti-noise | `AccessibilityMixin.eventFilter` |
| 3 | Alt+letter hygiene | `is_unmapped_alt_letter` |
| 4 | AccessibleDialog (JAWS/NVDA command Insert+T reads the right title) | `styled_dialogs.AccessibleDialog` |
| 5 | Default button only for one main action; Enter clicks the focused button in forms | `InfoDialog`, `AccessibleSampleWindow.keyPressEvent` |
| 5 | Date popup with Year, Month, and Day combo boxes, so the JAWS/NVDA command Insert+B reads it | `ReadDateDialog`, `DateComboFields` |
| 6 | Local F1, Escape, Alt+/ shortcuts; Ctrl+S Save | `AccessibleSampleWindow.setup_shortcuts` |
| 7 | F1 help as a one-column table dialog | `exec_shortcuts_dialog` |
| 8 | Focus safety (deselect on FocusIn) | `AccessibilityMixin.focus_deselect` |
| 9 | Tables read "name: value", not coordinates; visible selection | `set_accessible_table_rows`, `configure_table` |
| 11 | Dialog text read line by line, with no wrapped lines | `create_dialog_html_text`, `fit_dialog_width_to_text` |
| 12 | Plot line-by-line review | `PlotLineList` |
| 16 | Dialog open and close events | `announce_dialog_opened`, `announce_dialog_closed` |
| 17 | Tooltips separate from descriptions | `apply_tooltip_accessibility` |
| 18 | Message box over a dialog without "unavailable"; a box opened right after a dialog closes is read first | `exec_styled_message_box`; `InfoDialog` Test message box |
| 21 | No status announce while arrowing a table | `_on_table_selection_changed` |
| 22 | Tab exits the table | `make_accessible_table_key_press` |
| 23 | Window open: first focus in `showEvent`, no announce while hidden | `AccessibleSampleWindow.showEvent` |
| 24 | Focus returns to the field after a message box | `exec_styled_message_box`, `announce_status_message` |
| 25 | Typed year field when a screen reader is running | `make_year_field`, `validate_year_field` |

Sections 14 and 15 (screen reader detection, QAccessible startup) are in `accessibility_patterns.py`. Sections 26–28 and 30–41 describe AbCS production patterns the demo does not include: menus, progress windows, focus-out guards, date fields, dynamic Tab order, findable unavailable commands, keeping the user's place in lists, find and filter, tabbed windows, long operations, custom accessible interfaces, and low vision and platform notes.

## Shortcuts

- **F1** — keyboard shortcuts
- **Shift+F1** — context help stub
- **Alt+/** — read status
- **Ctrl+S** — save
- **Escape** — close with confirmation
- **Alt+T/C/Y** — Title, Category, Year fields
- **Alt+L** — Items table
- **Alt+D** — delete
- **Alt+I** — open the info dialog
- **Alt+P** — plot list
- **Alt+R** — set the read date for the selected item
- **Alt+Down** — open the category list

## Validation

Before changing a pattern, run the manual JAWS/NVDA check in implementation reference section 29: names on Tab, keyboard-only actions, Alt+/, focus after each dialog and message box, the JAWS/NVDA command Insert+T for titles, no "unavailable" before a box, tables read content, dialog text read once per line, value fields speak the new value, and Escape runs the same check as the close box.

## Using as a reference

1. Copy `accessibility_patterns.py` and `styled_dialogs.py` into your project
2. Inherit **`AccessibilityMixin` before `QDialog` subclasses** (see implementation reference §2 and §4)
3. Call `init_app_accessibility(app)` in `main()`
4. Follow `doc/PySide6_*.md`, and run the section 29 check after each UI change

## License

See [LICENSE](LICENSE). Non-commercial use; contact copyright holder for commercial licensing.
