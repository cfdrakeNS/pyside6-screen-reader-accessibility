# accessible_pySIde6_Sample

Standalone PySide6 reference application and documentation for screen-reader-friendly desktop UI patterns (JAWS, NVDA, Narrator, Orca).

**Repository:** https://github.com/cfdrakeNS/accessible_pySIde6_Sample

## Purpose

- Runnable demo of accessibility patterns documented in `doc/PySide6_*.md`
- Self-contained — no application framework dependencies
- Copy `accessibility_patterns.py` and `styled_dialogs.py` into your own PySide6 projects

## Relationship to AbCS

This project was extracted from [AbCS](https://github.com/cfdrakeNS/AbCS_Audio_book_Collector_Scanner) (Audio Book Collector Scanner). AbCS implements these patterns in production under `src/accessibility/` and `src/ui/` but does not bundle this repository.

## Install and run

```bash
cd C:\projects\accessible_pySIde6_Sample
pip install -r requirements.txt
python main.py
```

`psutil` is used for screen reader process detection on Windows; it is optional on Linux (detection falls back to `QAccessible.isActive()`).

## Repository layout

| File | Role |
|------|------|
| `main.py` | Demo window (`AccessibleSampleWindow`, `InfoDialog`) |
| `accessibility_patterns.py` | `AccessibilityMixin` and helper functions |
| `styled_dialogs.py` | `AccessibleDialog` and styled message boxes |
| `doc/PySide6_Accessibility_Patterns_and_Implementation_Reference.md` | Code patterns |
| `doc/PySide6_Screen_Reader_Accessibility_Best_Practices.md` | Design principles |

## Patterns demonstrated

| # | Pattern | Location |
|---|---------|----------|
| 1 | Status bar + Alt+/ readback | `accessibility_patterns.py`, `main.py` |
| 2 | Combo anti-noise | `AccessibilityMixin.eventFilter` |
| 3 | Alt+letter hygiene | `AccessibilityMixin.eventFilter` |
| 4 | AccessibleDialog (Insert+T) | `styled_dialogs.py`, `InfoDialog` |
| 5 | Modal dialog accessibility | `show_styled_message_box`, `InfoDialog` |
| 6 | Keyboard shortcuts | `main.py` |
| 7 | F1 / Shift+F1 help | `main.py` |
| 8 | Focus safety (deselect on FocusIn) | `AccessibilityMixin.focus_deselect` |
| 9 | Table semantics | `configure_table`, `main.py` |
| 11 | Read-only navigable text | `create_accessible_read_only_text` |
| 12 | Plot line-by-line review | `PlotLineList` |
| 14–22 | SR detection, QAccessible init, dialog events, tooltips, message boxes, selection announce, tab-exits-table | `accessibility_patterns.py`, `main.py` |

## Shortcuts

- **F1** — pattern help
- **Shift+F1** — context help stub
- **Alt+/** — read status
- **Escape** — close with confirmation
- **Alt+T/C/Y/I/L/S/D/O/P** — focus fields, buttons, plot list, info dialog

## Using as a reference

1. Copy `accessibility_patterns.py` and `styled_dialogs.py` into your project
2. Inherit **`AccessibilityMixin` before `QDialog` subclasses** (see implementation reference §2 and §4)
3. Call `init_app_accessibility(app)` in `main()`
4. Follow `doc/PySide6_*.md`

## License

See [LICENSE](LICENSE). Non-commercial use; contact copyright holder for commercial licensing.
