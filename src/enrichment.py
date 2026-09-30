from dataclasses import replace
import re
from src.identifiers import extract_identifiers

# Intentionally small Atlas vocabulary, not a general engineering ontology.
SCOPE_RULES = (
    ('motor mount', 'motor_mount', [('vibration', 'vibration')]),
    ('driver chip', 'motor_driver', [('lead time', 'lead_time')]),
    ('battery', 'battery_pack', [('thermal', 'thermal'), ('temperature', 'thermal')]),
    ('milestone', 'schedule', [('date', 'date'), ('schedule', 'date')]),
    ('power board', 'power_board', [('voltage', 'voltage'), ('current', 'current')]),
    ('chassis', 'chassis', [('clearance', 'clearance'), ('tolerance', 'tolerance')]),
    ('replacement motors', 'replacement_motors', [('delivery', 'delivery')]),
)


def has_term(text, term):
    return re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.IGNORECASE)


def enrich_message(message, cfg):
    text = message.text
    # Negated severity mentions must not create risk/blocker labels.
    severity_text = re.sub(r'\b(?:not|no) (?:a |an )?(?:build )?(?:blocker|risk)\b', '', text, flags=re.I)
    hits = []
    for topic, terms in cfg['keywords'].items():
        positions = [m.start() for term in terms if (m := has_term(text, term))]
        if positions:
            hits.append((min(positions), topic))
    topics = tuple(topic for _, topic in sorted(hits)[:3]) or ('design_decision',)
    if re.match(r'^(?:Lunch|Coffee|Thanks|Happy birthday|Anyone for|Great job|Emoji|Office|Weekend|Pizza)\b', text, re.I):
        kind = 'chatter'
    elif has_term(severity_text, 'blocker') or has_term(severity_text, 'blocked'):
        kind = 'blocker'
    elif has_term(severity_text, 'risk') or has_term(severity_text, 'unsafe'):
        kind = 'risk'
    elif has_term(text, 'decision') or has_term(text, 'approved'):
        kind = 'decision'
    elif any(has_term(text, word) for word in ('update', 'replaces', 'correction', 'completed', 'ready', 'confirmed')):
        kind = 'update'
    else:
        kind = 'fyi'
    affects = tuple(key for key, terms in cfg['affects_keywords'].items() if any(has_term(text, t) for t in terms))
    entity = metric = ''
    for marker, ent, metrics in SCOPE_RULES:
        if has_term(text, marker):
            for term, met in metrics:
                if has_term(text, term):
                    entity, metric = ent, met
                    break
            if entity:
                break
    return replace(message, topics=topics, message_type=kind, severity=cfg['severity'][kind],
                   affects=affects, entities=extract_identifiers(text, message.message_id), entity=entity, metric=metric)
