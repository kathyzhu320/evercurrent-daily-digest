from dataclasses import replace
from statistics import mean
from src.models import ScoreBreakdown, RankedStory
from src.personalization import active_priorities, decayed_preferences


def role_relevance(message, persona, cfg):
    role = max(cfg['role_topic'][t][persona.role] for t in message.topics)
    return max(role, cfg['owner_override_role_score']) if set(message.affects) & set(persona.owns) else role


def score_story(story, context, cfg):
    m, persona = story.representative, context.persona
    owns = tuple(sorted(set(m.affects) & set(persona.owns)))
    role = role_relevance(m, persona, cfg)
    active = set(active_priorities(context))
    matched = tuple(t for t in m.topics if t in active)
    priority = 1. if m.topics[0] in active else .6 if matched else 0.
    phase = max(cfg['phase_topic'][t][context.phase] for t in m.topics)
    severity = min(1., m.severity + min(.1, .025 * min(m.reply_count, 4)))
    age_hours = (context.as_of - m.timestamp).total_seconds() / 3600
    if age_hours < 0:
        raise ValueError('Future message must be filtered before ranking')
    recency = .5 ** (age_hours / cfg['recency_half_life_hours'])
    prefs = decayed_preferences(context.feedback, persona.persona_id, context.as_of, cfg)
    feedback = max(0., min(1., .5 + .5 * mean(prefs.get(t, 0.) for t in m.topics)))
    raw = dict(role=role, priority=priority, phase=phase, severity=severity, recency=recency, feedback=feedback)
    weighted = {key: value * cfg['weights'][key] for key, value in raw.items()}
    floor = m.message_type in ('blocker', 'risk') and role >= cfg['severity_floor']['min_role_relevance']
    breakdown = ScoreBreakdown(raw, weighted, sum(weighted.values()), matched, owns,
                              tuple(t for t in m.topics if cfg['role_topic'][t][persona.role] == max(cfg['role_topic'][x][persona.role] for x in m.topics)),
                              tuple(t for t in m.topics if cfg['phase_topic'][t][context.phase] == phase), floor)
    category = ('Action Required' if owns and m.message_type in ('blocker', 'risk') else
                'Risk & Blockers' if m.message_type in ('blocker', 'risk') else
                'Affects You' if owns else 'FYI')
    return RankedStory(story, breakdown, category)


def rank_key(item):
    return -item.score.final_score, -item.story.representative.timestamp.timestamp(), item.story.story_id


def protection_key(item):
    return (-item.score.raw['severity'], -item.score.raw['role'], -item.score.final_score,
            -item.story.representative.timestamp.timestamp(), item.story.story_id)


def select_top_k(ranked, cfg, use_floor=True):
    ranked = sorted(ranked, key=rank_key)
    if len({r.story.story_id for r in ranked}) != len(ranked):
        raise ValueError('Duplicate story IDs')
    k = cfg['top_k']
    protected = sorted((r for r in ranked if r.score.floor_eligible), key=protection_key)[:min(k, cfg['severity_floor']['max_items'])] if use_floor else []
    protected_ids = {r.story.story_id for r in protected}
    remaining = [r for r in ranked if r.story.story_id not in protected_ids][:k-len(protected)]
    return tuple(sorted([replace(r, protected=True) for r in protected] + [replace(r, protected=False) for r in remaining], key=rank_key))
