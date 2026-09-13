"""
icons.py — Inline SVG icon library (outline style, 1.5px stroke).

All icons use stroke="currentColor" so they inherit color from surrounding CSS.
Use the icon() helper to embed a sized, ready-to-render HTML string.

Icon set: custom outline SVGs consistent with Feather/Phosphor Regular weight.
Used only where icons add semantic meaning — not decoratively.
"""

# Raw SVG strings (24×24 viewBox, no size attributes — added by icon())
_SVGS: dict[str, str] = {

    # Water drop — water loss metric, flow chart label
    "drop": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>'
        '</svg>'
    ),

    # Bulleted list — ticket count metric
    "list": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="9" y1="6" x2="20" y2="6"/>'
        '<line x1="9" y1="12" x2="20" y2="12"/>'
        '<line x1="9" y1="18" x2="20" y2="18"/>'
        '<circle cx="4" cy="6" r="1" fill="currentColor" stroke="none"/>'
        '<circle cx="4" cy="12" r="1" fill="currentColor" stroke="none"/>'
        '<circle cx="4" cy="18" r="1" fill="currentColor" stroke="none"/>'
        '</svg>'
    ),

    # Building grid — zones metric
    "building": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="18" height="18"/>'
        '<path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>'
        '</svg>'
    ),

    # Waveform — sensor readings metric
    "activity": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'
        '</svg>'
    ),

    # Alert triangle — Critical severity
    "alert-triangle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 '
        '1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        '<line x1="12" y1="9" x2="12" y2="13"/>'
        '<line x1="12" y1="17" x2="12.01" y2="17"/>'
        '</svg>'
    ),

    # Circle with exclamation — High severity
    "alert-circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" y1="8" x2="12" y2="12"/>'
        '<line x1="12" y1="16" x2="12.01" y2="16"/>'
        '</svg>'
    ),

    # Circle with dash — Medium severity
    "minus-circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="8" y1="12" x2="16" y2="12"/>'
        '</svg>'
    ),

    # Empty circle — Low severity / generic fallback
    "circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5">'
        '<circle cx="12" cy="12" r="10"/>'
        '</svg>'
    ),

    # Clock — replay timer
    "clock": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/>'
        '</svg>'
    ),

    # Check circle — sensor OK status (Phase 2+)
    "check-circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
        '</svg>'
    ),

    # X circle — sensor FAULT/OFFLINE status (Phase 2+)
    "x-circle": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="15" y1="9" x2="9" y2="15"/>'
        '<line x1="9" y1="9" x2="15" y2="15"/>'
        '</svg>'
    ),
}


def icon(name: str, size: int = 16) -> str:
    """
    Return an HTML SVG string for the named icon at the given pixel size.
    Color is inherited from surrounding CSS via currentColor.

    Args:
        name: icon name (see _SVGS keys above)
        size: pixel size for width and height attributes (default 16)

    Returns:
        HTML string ready to embed in st.markdown(unsafe_allow_html=True) content.
    """
    svg = _SVGS.get(name, _SVGS["circle"])
    return svg.replace(
        "<svg ",
        (
            f'<svg width="{size}" height="{size}" '
            f'style="display:inline-block;vertical-align:middle;flex-shrink:0;" '
        ),
        1,
    )
