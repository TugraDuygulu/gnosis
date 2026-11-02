"""Display helpers for the staff workspace templates."""

import os
from decimal import Decimal, InvalidOperation

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    """Static URL with the file's modification time, so browsers drop stale copies."""
    url = static(path)
    found = finders.find(path)
    if found:
        url += f"?v={int(os.path.getmtime(found))}"
    return url

# Achievement colour scale from DESIGN.md: brick (0) to deep green (100).
FILL_STOPS = (
    (0, (166, 61, 61)), (40, (194, 101, 42)), (60, (192, 138, 43)),
    (75, (125, 139, 53)), (85, (62, 123, 85)), (100, (45, 106, 79)),
)
TEXT_STOPS = (
    (0, (142, 47, 47)), (40, (159, 76, 23)), (60, (143, 101, 20)),
    (75, (91, 103, 36)), (85, (46, 99, 67)), (100, (36, 86, 63)),
)


def _percent(value):
    try:
        number = float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return min(max(number, 0.0), 100.0)


def _mix(stops, value):
    for (low, a), (high, b) in zip(stops, stops[1:]):
        if value <= high:
            t = (value - low) / (high - low)
            return "#" + "".join(f"{round(x + t * (y - x)):02X}" for x, y in zip(a, b))
    return "#" + "".join(f"{x:02X}" for x in stops[-1][1])


@register.filter
def score_fill(value):
    """Bar colour for an achievement percentage."""
    value = _percent(value)
    return "" if value is None else _mix(FILL_STOPS, value)


@register.filter
def score_text(value):
    """Text colour (AA on white) for an achievement percentage."""
    value = _percent(value)
    return "" if value is None else _mix(TEXT_STOPS, value)


@register.filter
def pct(value):
    """A 0-100 number safe to use as a CSS length percentage."""
    value = _percent(value)
    return "0" if value is None else f"{value:.2f}"


@register.filter
def initials(name):
    parts = str(name).split()
    if len(parts) > 1:
        parts = [parts[0], parts[-1]]
    return "".join(part[0] for part in parts).upper() or "?"
