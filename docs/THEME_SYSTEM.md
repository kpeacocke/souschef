# Theme System

SousChef supports four appearance modes:

- `light`
- `dark`
- `high_contrast`
- `auto` (resolves to light or dark based on OS preference)

## Persistence

Theme preference is persisted in:

- `~/.souschef/theme.json`

The preference is loaded at startup and cached in `st.session_state.souschef_theme`.

## Centralised Tokens

Theme tokens are defined in `souschef/ui/theme.py` via `THEME_TOKENS`.

Each resolved theme (`light`, `dark`, `high_contrast`) provides:

- `bg`
- `surface`
- `text`
- `muted`
- `border`
- `focus_ring`
- `accent`

## Accessibility Notes

The `high_contrast` mode intentionally uses:

- Maximum foreground/background contrast (`#ffffff` on `#000000`)
- Strong focus indicators (`focus_ring`)
- Explicit button borders and hover states

This supports WCAG-oriented workflows and keyboard navigation.

## Visual Snapshot Strategy

Visual regression is validated with deterministic CSS snapshots in unit tests:

- `tests/unit/test_ui_theme_snapshots.py`

The snapshot assertions lock in colour tokens and focus styles to prevent accidental regressions.
