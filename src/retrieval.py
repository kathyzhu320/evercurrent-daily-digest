"""Authorized-pool TF-IDF. No global index or private vocabulary reaches queries."""
from datetime import timedelta
import hashlib
import json
import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from src.models import utc
from src.personalization import active_priorities
from src.enrichment import has_term
from src.identifiers import extract_identifiers


def filter_authorized_messages(messages, context, cfg):
    utc(context.as_of)
    start = context.as_of - timedelta(hours=cfg['lookback_hours'])
    return tuple(sorted((m for m in messages if m.channel in context.persona.channels
                         and m.project == context.project and start <= m.timestamp <= context.as_of
                         and m.message_type != 'chatter'), key=lambda m: m.message_id))


def content_fingerprint(messages):
    rows = [(m.message_id, m.text, m.channel, m.timestamp.isoformat(), m.project) for m in messages]
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def index_manifest(messages):
    return {'backend': 'tfidf', 'ordered_message_ids': [m.message_id for m in messages],
            'content_fingerprint': content_fingerprint(messages), 'persistent_vectors': False}


def validate_index_manifest(messages, manifest):
    if manifest != index_manifest(messages):
        raise ValueError('Stale or misaligned TF-IDF manifest')


def retrieve_candidates(eligible, context, cfg, top_n=None):
    # eligible is the only input corpus: ACL filtering is a pipeline prerequisite.
    if not eligible:
        return (), {}
    n = cfg['candidate_top_n'] if top_n is None else top_n
    if n < 0:
        raise ValueError('top_n must be nonnegative')
    priorities = active_priorities(context)
    role_words = [t for t in cfg['keywords'] if cfg['role_topic'][t][context.persona.role] >= .8]
    phase_words = [t for t in cfg['keywords'] if cfg['phase_topic'][t][context.phase] >= .8]
    query = ' '.join(term for t in priorities + tuple(role_words) + tuple(phase_words) for term in cfg['keywords'][t])
    query += ' ' + ' '.join(context.exact_terms)
    vectorizer = TfidfVectorizer(lowercase=True, token_pattern=r'(?u)\b[\w-]+\b', norm='l2')
    try:
        matrix = vectorizer.fit_transform([m.text for m in eligible])
        similarities = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
    except ValueError as e:
        if 'empty vocabulary' not in str(e):
            raise
        similarities = np.zeros(len(eligible))
    order = sorted(range(len(eligible)), key=lambda i: (-float(similarities[i]), eligible[i].message_id))[:n]
    reasons = {}
    def add(m, reason):
        reasons.setdefault(m.message_id, set()).add(reason)
    for i in order:
        add(eligible[i], 'tfidf')
    for m in eligible:
        if set(priorities) & set(m.topics) or any(has_term(m.text, term) for t in priorities for term in cfg['keywords'][t]):
            add(m, 'priority_keyword')
        if any(has_term(m.text, term) for term in context.exact_terms):
            add(m, 'exact_term')
    identifiers = {e.key for m in eligible if m.message_id in reasons for e in m.entities}
    identifiers |= {e.key for term in context.exact_terms for e in extract_identifiers(term, 'QUERY')}
    for m in eligible:
        if identifiers & {e.key for e in m.entities}:
            add(m, 'identifier_union')
    # Preserve the entire authorized factual neighborhood, independent of persona/phase.
    threads = {m.thread_id for m in eligible if m.message_id in reasons}
    scopes = {(m.entity, m.metric) for m in eligible if m.message_id in reasons and m.entity and m.metric}
    for m in eligible:
        if m.thread_id in threads:
            add(m, 'thread_context')
        if m.entity and (m.entity, m.metric) in scopes:
            add(m, 'fact_context')
    return tuple(m for m in eligible if m.message_id in reasons), {k: tuple(sorted(v)) for k, v in sorted(reasons.items())}
