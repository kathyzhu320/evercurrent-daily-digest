import json
from dataclasses import replace
from src.models import Message, Persona, utc
from src.config import ROOT, CHANNELS, PHASES, ROLES, TOPICS
from src.enrichment import enrich_message


def load_messages(path=None, cfg=None):
    from src.config import load_config
    cfg = cfg or load_config()
    rows = json.loads((path or ROOT / 'data/slack_messages.json').read_text())
    messages = []
    # Derived fields are recomputed, never trusted as runtime labels.
    raw_fields = ('message_id', 'channel', 'timestamp', 'author', 'author_role', 'thread_id',
                  'text', 'project', 'phase', 'parent_id', 'reactions')
    for row in rows:
        raw = {key: row[key] for key in raw_fields if key in row}
        raw['timestamp'] = utc(raw['timestamp'])
        messages.append(enrich_message(Message(**raw), cfg))
    validate_dataset(messages)
    return tuple(sorted(messages, key=lambda m: (m.timestamp, m.message_id)))


def load_personas(path=None):
    rows = json.loads((path or ROOT / 'data/users.json').read_text())
    result = {}
    for row in rows:
        for key in ('owns', 'channels', 'default_priorities'):
            row[key] = tuple(row[key])
        persona = Persona(**row)
        if persona.role not in ROLES or not set(persona.channels) <= set(CHANNELS):
            raise ValueError('Invalid persona membership')
        if not set(persona.default_priorities) <= set(TOPICS):
            raise ValueError('Invalid persona priorities')
        if persona.persona_id in result:
            raise ValueError('Duplicate persona ID')
        result[persona.persona_id] = persona
    return result


def validate_dataset(messages):
    ids = [m.message_id for m in messages]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate message ID')
    lookup = {m.message_id: m for m in messages}
    for m in messages:
        utc(m.timestamp)
        if m.channel not in CHANNELS or m.phase not in PHASES or m.author_role not in ROLES:
            raise ValueError('Invalid message metadata')
        if not 1 <= len(m.topics) <= 3 or len(set(m.topics)) != len(m.topics) or not set(m.topics) <= set(TOPICS):
            raise ValueError('Invalid topics')
        if not m.text or not m.thread_id or m.reactions < 0 or m.reply_count < 0:
            raise ValueError('Invalid text/thread/count')
        if m.parent_id:
            parent = lookup.get(m.parent_id)
            if parent is None or parent.thread_id != m.thread_id or parent.timestamp > m.timestamp:
                raise ValueError('Invalid parent')
        for e in m.entities:
            if e.source_message_id != m.message_id or m.text[e.start:e.end] != e.raw:
                raise ValueError('Invalid identifier provenance')


def count_authorized_replies(messages):
    replies = {}
    for m in messages:
        if m.parent_id:
            replies.setdefault(m.thread_id, set()).add(m.message_id)
    return tuple(replace(m, reply_count=len(replies.get(m.thread_id, ()))) for m in messages)
