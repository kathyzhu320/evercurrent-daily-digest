"""Dataset-driven typed identifiers, preserving values, units and source spans."""
import re
from decimal import Decimal
from src.models import Identifier

NUMBER = r'\d+(?:\.\d+)?'
PATTERNS = [
    ('voltage', rf'\b({NUMBER})\s*(V)\b'),
    ('current', rf'\b({NUMBER})\s*(mA|A)\b'),
    ('speed', rf'\b({NUMBER})\s*(RPM)\b'),
    ('vibration', rf'\b({NUMBER})\s*(mm/s|g|Hz)\b'),
    ('lead_time', rf'\b({NUMBER})\s*(weeks?|wks?|days?)\b'),
    ('temperature', rf'(?<![\w.])(-?{NUMBER})\s*(°?C)\b'),
    ('percentage', rf'\b({NUMBER})\s*(%)'),
    ('revision', r'\b(rev\s+[A-Z])\b'),
    ('version', r'\b(v\d+(?:\.\d+)+)\b'),
    ('part', r'\b([A-Z]{2,}-\d{3,}[A-Z0-9-]*)\b'),
    ('date', r'\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'),
    ('error', r'\b(E\d{3})\b'),
]
UNIT_MAP = {'v': 'V', 'a': 'A', 'ma': 'mA', 'rpm': 'RPM', 'mm/s': 'mm/s',
            'g': 'g', 'hz': 'Hz', 'c': 'C', '°c': 'C', '%': '%',
            'week': 'weeks', 'weeks': 'weeks', 'wk': 'weeks', 'wks': 'weeks',
            'day': 'days', 'days': 'days'}


def extract_identifiers(text, source_message_id):
    out = []
    for kind, pattern in PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1)
            unit = ''
            if match.lastindex == 2:
                value = str(Decimal(value).normalize())
                # Decimal's exponent form is not useful for engineering display.
                value = format(Decimal(value), 'f')
                unit = UNIT_MAP[match.group(2).lower()]
            else:
                value = re.sub(r'\s+', ' ', value).upper()
            out.append(Identifier(kind, value, unit, match.group(), match.start(), match.end(), source_message_id))
    return tuple(sorted(out, key=lambda e: (e.start, e.kind)))


def identifier_sets(message):
    result = {}
    for item in message.entities:
        result.setdefault(item.kind, set()).add((item.value, item.unit))
    return result


def differing_identifiers(messages):
    by_kind = {}
    for msg in messages:
        for kind, values in identifier_sets(msg).items():
            by_kind.setdefault(kind, {})[msg.message_id] = sorted(values)
    return {kind: sources for kind, sources in sorted(by_kind.items())
            if len({tuple(values) for values in sources.values()}) > 1}


def mask_identifiers(message):
    text = message.text
    for item in sorted(message.entities, key=lambda e: e.start, reverse=True):
        text = text[:item.start] + ' ' + item.kind + ' ' + text[item.end:]
    return text
