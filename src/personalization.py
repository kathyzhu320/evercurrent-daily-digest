from datetime import timedelta
from src.models import Priority, FeedbackEvent, UserContext, utc
from src.config import TOPICS


def make_priorities(topics, as_of, ttl_days=7):
    as_of = utc(as_of)
    if not set(topics) <= set(TOPICS):
        raise ValueError('Unknown priority topic')
    return tuple(Priority(t, as_of, as_of + timedelta(days=ttl_days)) for t in dict.fromkeys(topics))


def active_priorities(context):
    return tuple(p.topic for p in context.priorities if p.created_at <= context.as_of < p.expires_at)


def apply_feedback(events, event):
    utc(event.timestamp)
    if not set(event.topics) <= set(TOPICS) or not event.topics:
        raise ValueError('Invalid feedback topics')
    existing = [e for e in events if e.event_id == event.event_id]
    if existing:
        if existing[0] != event:
            raise ValueError('Conflicting duplicate event ID')
        return tuple(events)
    return tuple(events) + (event,)


def decayed_preferences(events, persona_id, as_of, cfg):
    as_of = utc(as_of)
    values, times, seen = {}, {}, set()
    for e in sorted(events, key=lambda e: (e.timestamp, e.event_id)):
        if e.event_id in seen:
            continue
        seen.add(e.event_id)
        if e.persona_id != persona_id or e.timestamp > as_of:
            continue
        for topic in dict.fromkeys(e.topics):
            if topic in times:
                age = (e.timestamp - times[topic]).total_seconds() / 86400
                values[topic] *= .5 ** (age / cfg['feedback']['half_life_days'])
            values[topic] = max(-1., min(1., values.get(topic, 0.) + (1 if e.relevant else -1) * cfg['feedback']['step']))
            times[topic] = e.timestamp
    return {t: v * .5 ** (((as_of - times[t]).total_seconds() / 86400) / cfg['feedback']['half_life_days']) for t, v in values.items()}


def make_context(persona, cfg, phase=None, priorities=None, as_of=None, feedback=(), exact_terms=()):
    clock = utc(as_of or cfg['as_of'])
    return UserContext(persona, phase or cfg['default_phase'],
                       make_priorities(persona.default_priorities if priorities is None else priorities,
                                       clock, cfg['priority_default_ttl_days']), clock, tuple(feedback), cfg['project'], tuple(exact_terms))
