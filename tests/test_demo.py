from dataclasses import replace
from src.demo import build_demo_digest, record_feedback, top3_jaccard
from src.personalization import make_context
from src.pipeline import build_ranked_digest
from src.presentation import relationship_label, score_rows, source_rows, story_marker, why_this_matters
from src.summarizer import SummaryCache
from scripts.acceptance import floor_fixture


def find_story(result, id):
    return next(r for r in result.ranked if r.story.story_id == id)


def test_comparable_conflict_and_unresolved_wording(cfg, messages, personas):
    sarah = build_ranked_digest(make_context(personas['sarah'], cfg), messages, cfg)
    priya = build_ranked_digest(make_context(personas['priya'], cfg), messages, cfg)
    vibration = find_story(sarah, 'S-M001').story
    thermal = find_story(priya, 'S-M009').story
    voltage = find_story(priya, 'S-M012').story
    assert story_marker(vibration) == 'Conflict — sources report different values'
    assert any(relationship_label(r).startswith('Conflict') for r in vibration.relationships if r.comparable)
    assert any(relationship_label(r).startswith('Unresolved difference') for r in vibration.relationships if not r.comparable and r.label == 'CONFLICT')
    for story in (thermal, voltage):
        assert story.label == 'CONFLICT'  # Gate 1 classification is untouched.
        assert story_marker(story).startswith('Unresolved difference')
        assert all(not r.comparable for r in story.relationships)
        assert all('contradictory' not in relationship_label(r).lower() for r in story.relationships)


def test_why_ranked_is_direct_gate1_breakdown(cfg, messages, personas):
    item = build_ranked_digest(make_context(personas['sarah'], cfg), messages, cfg).digest[0]
    rows = score_rows(item)
    assert [r['Signal'] for r in rows] == ['Role', 'Priority', 'Phase', 'Severity', 'Recency', 'Feedback']
    assert {r['Signal'].lower(): r['Raw sub-score'] for r in rows} == item.score.raw
    assert {r['Signal'].lower(): r['Weighted contribution'] for r in rows} == item.score.weighted
    assert 'integration' in why_this_matters(item)
    assert 'Severity Floor' in why_this_matters(item)
    assert len(source_rows(item.story)) == len(item.story.source_message_ids)


def test_feedback_changes_next_score_without_bypassing_floor(cfg, personas, tmp_path):
    from src.retrieval import filter_authorized_messages
    fixture, ctx = floor_fixture(cfg, personas['sarah'])
    cache = SummaryCache(tmp_path / 'cache.json')
    before = build_demo_digest(replace(ctx, feedback=()), fixture, cfg, cache)
    risk = next(x.ranked for x in before.items if x.ranked.story.story_id == 'S-F900')
    events = ()
    for i in range(5):
        events = record_feedback(events, risk, 'sarah', ctx.as_of, False, f'E-{i}')
    assert len(record_feedback(events, risk, 'sarah', ctx.as_of, False, 'E-4')) == 5
    after = build_demo_digest(replace(ctx, feedback=events), fixture, cfg, cache)
    protected = next(x.ranked for x in after.items if x.ranked.story.story_id == 'S-F900')
    assert protected.protected and protected.score.raw['feedback'] == 0
    assert len(after.items) == 5
    assert set(before.result.eligible_ids) == set(after.result.eligible_ids)


def test_persona_feedback_isolated(cfg, messages, personas):
    sarah = make_context(personas['sarah'], cfg)
    before = build_ranked_digest(sarah, messages, cfg)
    item = before.digest[0]
    events = record_feedback((), item, 'sarah', sarah.as_of, True, 'ONE')
    updated = build_ranked_digest(replace(sarah, feedback=events), messages, cfg)
    assert find_story(updated, item.story.story_id).score.raw['feedback'] > item.score.raw['feedback']
    raj = make_context(personas['raj'], cfg, feedback=events)
    raj_before = build_ranked_digest(make_context(personas['raj'], cfg), messages, cfg)
    assert [r.score.final_score for r in build_ranked_digest(raj, messages, cfg).ranked] == [r.score.final_score for r in raj_before.ranked]


def test_compare_same_context_different_personas(cfg, messages, personas):
    outputs = {id: build_ranked_digest(make_context(personas[id], cfg), messages, cfg)
               for id in ('sarah', 'raj', 'marcus')}
    assert outputs['sarah'].as_of == outputs['raj'].as_of == outputs['marcus'].as_of
    assert top3_jaccard(outputs['sarah'], outputs['raj']) == 0
    assert top3_jaccard(outputs['sarah'], outputs['marcus']) == 0
    assert top3_jaccard(outputs['raj'], outputs['marcus']) == 0


def test_deterministic_difference_summary_separates_comparable_pair(cfg, messages, personas):
    from src.summarizer import deterministic_summary
    sarah = build_ranked_digest(make_context(personas['sarah'], cfg), messages, cfg)
    priya = build_ranked_digest(make_context(personas['priya'], cfg), messages, cfg)
    vibration = deterministic_summary(find_story(sarah, 'S-M001').story)
    thermal = deterministic_summary(find_story(priya, 'S-M009').story)
    voltage = deterministic_summary(find_story(priya, 'S-M012').story)
    assert 'M001 4.2 mm/s; M002 6.8 mm/s' in vibration
    assert 'Other source comparisons have different or unverified test conditions' in vibration
    assert '3000 RPM' not in vibration  # Do not imply that run contradicts the 2000 RPM pair.
    for text in (thermal, voltage):
        assert text.startswith('Unresolved difference')
        assert 'contradictory' not in text.lower()
