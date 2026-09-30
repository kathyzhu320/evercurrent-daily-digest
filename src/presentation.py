"""Wording and explanation adapters over immutable Gate 1 story/score data."""
from src.models import RankedStory, Relationship, Story

SIGNALS = ('role', 'priority', 'phase', 'severity', 'recency', 'feedback')
CATEGORY_ORDER = ('Action Required', 'Risk & Blockers', 'Affects You', 'FYI')


def relationship_label(relationship: Relationship) -> str:
    if relationship.label == 'CONFLICT':
        return ('Conflict — sources report different values' if relationship.comparable
                else 'Unresolved difference — test conditions differ or are not established')
    return {'SUPERSEDED': 'Updated — prior value retained',
            'DUPLICATE': 'Repeated report'}.get(relationship.label, '')


def story_marker(story: Story) -> str:
    if any(r.label == 'CONFLICT' and r.comparable for r in story.relationships):
        return 'Conflict — sources report different values'
    if any(r.label == 'CONFLICT' for r in story.relationships):
        return 'Unresolved difference — values differ across conditions or unverified conditions'
    if any(r.label == 'SUPERSEDED' for r in story.relationships):
        return 'Updated — prior value retained'
    if any(r.label == 'DUPLICATE' for r in story.relationships):
        return 'Repeated report'
    return ''


def why_this_matters(item: RankedStory) -> str:
    score = item.score
    reasons = []
    if score.owns_affects:
        reasons.append('affects ' + ', '.join(score.owns_affects) + ' you own')
    elif score.role_topics:
        reasons.append('matches your role via ' + ', '.join(score.role_topics))
    if score.matched_priorities:
        reasons.append('matches current priority ' + ', '.join(score.matched_priorities))
    if score.phase_topics:
        reasons.append('relevant in this phase via ' + ', '.join(score.phase_topics))
    if item.protected:
        reasons.append('retained by the Severity Floor')
    return '; '.join(reasons) + '.'


def score_rows(item: RankedStory) -> list[dict]:
    return [{'Signal': key.title(), 'Raw sub-score': item.score.raw[key],
             'Weighted contribution': item.score.weighted[key]} for key in SIGNALS]


def source_rows(story: Story) -> list[dict]:
    return [{'ID': msg.message_id, 'Channel': '#' + msg.channel,
             'UTC timestamp': msg.timestamp.isoformat().replace('+00:00', 'Z'),
             'Text': msg.text,
             'Role': 'representative' if msg.message_id == story.representative.message_id else 'source/context'}
            for msg in sorted({m.message_id: m for m in story.messages + story.context_messages}.values(),
                              key=lambda m: (m.timestamp, m.message_id))]
