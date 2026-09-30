from dataclasses import replace
from src.models import DigestResult
from src.config import PHASES
from src.ingestion import count_authorized_replies
from src.retrieval import filter_authorized_messages, retrieve_candidates
from src.conflicts import group_and_classify
from src.ranking import role_relevance, score_story, select_top_k, rank_key


def build_ranked_digest(context, messages, cfg, top_n=None):
    if context.phase not in PHASES:
        raise ValueError('Unknown phase')
    eligible = count_authorized_replies(filter_authorized_messages(messages, context, cfg))
    candidates, reasons = retrieve_candidates(eligible, context, cfg, top_n)
    candidate_ids = {m.message_id for m in candidates}
    # Restore all eligible risk evidence before grouping. Floor uses the full authorized pool.
    for m in eligible:
        if m.message_type in ('risk', 'blocker') and role_relevance(m, context.persona, cfg) >= cfg['severity_floor']['min_role_relevance']:
            candidate_ids.add(m.message_id)
            reasons[m.message_id] = tuple(sorted(set(reasons.get(m.message_id, ())) | {'floor_pool'}))
    # Complete facts for risk/restored seeds as well, so context changes cannot alter representatives.
    scopes = {(m.entity, m.metric) for m in eligible if m.message_id in candidate_ids and m.entity}
    threads = {m.thread_id for m in eligible if m.message_id in candidate_ids}
    for m in eligible:
        if (m.entity and (m.entity, m.metric) in scopes) or m.thread_id in threads:
            candidate_ids.add(m.message_id)
            reasons[m.message_id] = tuple(sorted(set(reasons.get(m.message_id, ())) | {'authorized_context'}))
    candidates = tuple(m for m in eligible if m.message_id in candidate_ids)
    stories = group_and_classify(candidates, cfg, similarity_messages=eligible)
    ranked = []
    for story in stories:
        member_ids = {m.message_id for m in story.messages}
        member_threads = {m.thread_id for m in story.messages}
        context_messages = tuple(m for m in eligible if m.thread_id in member_threads and m.message_id not in member_ids)
        story = replace(story, context_messages=context_messages)
        ranked.append(score_story(story, context, cfg))
    ranked = tuple(sorted(ranked, key=rank_key))
    digest = select_top_k(ranked, cfg)
    protected_ids = {r.story.story_id for r in digest if r.protected}
    ranked = tuple(replace(r, protected=r.story.story_id in protected_ids) for r in ranked)
    return DigestResult(context.as_of, tuple(m.message_id for m in eligible), tuple(sorted(candidate_ids)),
                        dict(sorted(reasons.items())), ranked, digest)
