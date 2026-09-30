"""Identifier-level summary guard over the authorized sources of one story.

This does not verify causal, temporal, or semantic relationships between facts.
"""
from dataclasses import dataclass
from decimal import Decimal
import re
from src.identifiers import extract_identifiers
from src.models import Message

BARE_NUMBER = re.compile(r'(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])')


@dataclass(frozen=True)
class FaithfulnessResult:
    ok: bool
    checked_count: int
    unsupported: tuple[str, ...]


def _facts(text: str) -> tuple[tuple[str, str, str], ...]:
    identifiers = extract_identifiers(text, 'GUARD')
    facts = [(item.kind, item.value, item.unit) for item in identifiers]
    # Mask typed spans before looking for bare numbers. A bare 24 must not gain
    # support from an authorized 24V source when the unit has been dropped.
    masked = list(text)
    for item in identifiers:
        masked[item.start:item.end] = ' ' * (item.end-item.start)
    for match in BARE_NUMBER.finditer(''.join(masked)):
        facts.append(('number', format(Decimal(match.group()), 'f'), ''))
    return tuple(facts)


def check_faithfulness(summary: str, authorized_sources: tuple[Message, ...]) -> FaithfulnessResult:
    if not isinstance(summary, str) or not summary.strip() or not authorized_sources:
        return FaithfulnessResult(False, 0, ('missing summary or authorized source',))
    allowed = {fact for msg in authorized_sources for fact in _facts(msg.text)}
    found = _facts(summary)
    missing = tuple(sorted({f'{kind}:{value}{unit}' for kind, value, unit in found if (kind, value, unit) not in allowed}))
    return FaithfulnessResult(not missing, len(found), missing)
