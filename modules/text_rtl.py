"""Robust Persian/Arabic RTL text shaping for PIL."""
import os

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAVE = True
except Exception:
    _HAVE = False


def shape(text: str) -> str:
    """Return display-ready (visually ordered) text for PIL."""
    if not _HAVE:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def wrap_rtl(text: str, max_chars: int = 22):
    """Greedy word-wrap that keeps RTL order; returns list of lines."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_lines(text: str, max_chars: int = 22, max_lines: int = 4):
    lines = wrap_rtl(text, max_chars)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max_chars - 1] + "…"
    return [shape(l) for l in lines]
