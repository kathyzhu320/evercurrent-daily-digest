"""Conservative Atlas factual relationships, retaining pair-level evidence."""
from itertools import combinations
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from src.models import Relationship, Story
from src.identifiers import differing_identifiers, mask_identifiers, identifier_sets


def canonical_fact(message):
    text = message.text
    text = re.sub(r'^(?:Forwarded:\s*|FYI:\s*|Risk:\s*|Update (?:replaces|corrects) M\d+:\s*|Correction (?:replaces|corrects) M\d+:\s*)+', '', text, flags=re.I)
    return re.sub(r'\s+', ' ', text).strip().lower()


def same_scope(a, b):
    if not a.entity or not a.metric or (a.entity, a.metric) != (b.entity, b.metric):
        return False
    pa, pb = identifier_sets(a).get('part', set()), identifier_sets(b).get('part', set())
    return pa == pb


def explicitly_replaces(old, new):
    return (new.timestamp > old.timestamp and same_scope(old, new)
            and re.search(r'\b(?:update|correction)\s+(?:replaces|corrects)\s+' + re.escape(old.message_id) + r'\b', new.text, re.I) is not None)


def comparable_conditions(a, b):
    def condition(m):
        bench = re.search(r'\bbench\s+[A-Z]\b', m.text, re.I)
        load = re.search(r'\b(?:no-load|loaded|unloaded)\b', m.text, re.I)
        ids = identifier_sets(m)
        return (bench.group().lower() if bench else None,
                load.group().lower() if load else None,
                tuple(sorted(ids.get('speed', set()))), tuple(sorted(ids.get('voltage', set()))),
                tuple(sorted(ids.get('revision', set()))), tuple(sorted(ids.get('temperature', set()))))
    ca, cb = condition(a), condition(b)
    # Restrict the positive scientific claim to vibration on an explicit bench/load/speed.
    return a.metric == 'vibration' and ca == cb and ca[0] is not None and ca[1] is not None and bool(ca[2])


def group_and_classify(messages, cfg, similarity_messages=None):
    if not messages:
        return ()
    messages = tuple(sorted(messages, key=lambda m: m.message_id))
    # Identifier masking is for lexical grouping only, never for evidence or retrieval.
    texts = [mask_identifiers(m) for m in (similarity_messages or messages)]
    vectorizer = TfidfVectorizer(token_pattern=r'(?u)\b[\w-]+\b')
    try:
        vectorizer.fit(texts)
        matrix = vectorizer.transform([mask_identifiers(m) for m in messages])
        similarities = (matrix @ matrix.T).toarray()
    except ValueError as e:
        if 'empty vocabulary' not in str(e):
            raise
        similarities = [[0.] * len(messages) for _ in messages]
    parent = list(range(len(messages)))
    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i
    def union(i, j):
        parent[find(j)] = find(i)
    relations = []
    pairs = []
    for i, j in combinations(range(len(messages)), 2):
        a, b = messages[i], messages[j]
        if not same_scope(a, b) or a.topics[0] != b.topics[0]:
            continue
        old, new = sorted((a, b), key=lambda m: (m.timestamp, m.message_id))
        differences = differing_identifiers((a, b))
        if explicitly_replaces(old, new):
            label = 'SUPERSEDED'
            ids = (old.message_id, new.message_id)
            reason = f'{new.message_id} explicitly replaces/corrects {old.message_id}; same entity={old.entity}, metric={old.metric}'
        elif canonical_fact(a) == canonical_fact(b) and not differences:
            label, ids = 'DUPLICATE', (a.message_id, b.message_id)
            reason = 'Equivalent factual clause and identical typed identifiers; attribution prefix ignored'
        else:
            if differences and similarities[i][j] >= cfg['conflict']['similarity_threshold']:
                pairs.append((i, j, differences, float(similarities[i][j])))
            continue
        relations.append(Relationship(label, ids, reason, differences))
        union(i, j)
    # A directed ancestry path resolves old/new differences. Two competing updates
    # from the same ancestor are NOT resolved merely because they share that root.
    adjacency = {}
    for r in relations:
        old_id, new_id = r.source_ids
        adjacency.setdefault(old_id, set()).add(new_id)
        if r.label == 'DUPLICATE':
            adjacency.setdefault(new_id, set()).add(old_id)
    def reaches(start, target):
        pending, seen = [start], set()
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node not in seen:
                seen.add(node)
                pending.extend(adjacency.get(node, ()))
        return False
    for i, j, diffs, sim in pairs:
        aid, bid = messages[i].message_id, messages[j].message_id
        if reaches(aid, bid) or reaches(bid, aid):
            continue
        a, b = messages[i], messages[j]
        comparable = comparable_conditions(a, b)
        reason = (f'Same entity={a.entity}, metric={a.metric}; masked TF-IDF cosine={sim:.6f}; '
                  + ('same bench/load/RPM: comparable-fact discrepancy, unresolved' if comparable
                     else 'conditions differ or are insufficiently documented; unresolved differences, not a scientific contradiction'))
        relations.append(Relationship('CONFLICT', (a.message_id, b.message_id), reason, diffs, comparable))
        union(i, j)
    groups = {}
    for i, message in enumerate(messages):
        groups.setdefault(find(i), []).append(message)
    result = []
    for group in groups.values():
        ids = {m.message_id for m in group}
        rels = tuple(r for r in relations if set(r.source_ids) <= ids)
        labels = {r.label for r in rels}
        label = next((l for l in ('CONFLICT', 'SUPERSEDED', 'DUPLICATE') if l in labels), 'SINGLE')
        if label == 'CONFLICT':
            representative = min(group, key=lambda m: (-m.severity, -m.timestamp.timestamp(), m.message_id))
        else:
            replaced = {r.source_ids[0] for r in rels if r.label == 'SUPERSEDED'}
            # A duplicate of an explicitly replaced historical fact is historical too.
            changed = True
            while changed:
                before = set(replaced)
                for r in rels:
                    if r.label == 'DUPLICATE' and set(r.source_ids) & replaced:
                        replaced.update(r.source_ids)
                changed = before != replaced
            terminals = {r.source_ids[1] for r in rels if r.label == 'SUPERSEDED'} - replaced
            current = [m for m in group if m.message_id in terminals] if label == 'SUPERSEDED' and terminals else [m for m in group if m.message_id not in replaced]
            current = current or group
            representative = min(current, key=lambda m: (-m.timestamp.timestamp(), m.message_id))
        result.append(Story('S-' + min(ids), tuple(group), representative, label, rels,
                            differing_identifiers(group)))
    return tuple(sorted(result, key=lambda s: s.story_id))
