"""LaTeX sanitizer — escape special characters for safe LaTeX output."""

from __future__ import annotations

import re

# Regex matching any LaTeX-special character (including backslash)
_SPECIAL_RE = re.compile(r"([\\&%$#_{}~^])")

# Replacement map for single-char matches
_REPLACEMENTS: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def sanitize_for_latex(text: str) -> str:
    """Escape special LaTeX characters in user-provided text.

    Uses a single regex pass to avoid double-escaping issues
    (e.g., backslash replacement introducing braces that then
    get re-escaped).
    """
    return _SPECIAL_RE.sub(lambda m: _REPLACEMENTS[m.group(1)], text)
