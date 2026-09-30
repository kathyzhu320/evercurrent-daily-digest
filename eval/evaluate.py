"""Offline evaluation against independently reviewed labels; never changes runtime ranking."""
from dataclasses import replace
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load_config
from src.conflicts import group_and_classify
from src.demo import build_demo_digest, top3_jaccard
from src.faithfulness import check_faithfulness
from src.ingestion import load_messages, load_personas
from src.models import FeedbackEvent, utc
from src.personalization import make_context, make_priorities
from src.pipeline import build_ranked_digest
from src.retrieval import filter_authorized_messages
from src.summarizer import summarize_story

LABELS_PATH = Path(__file__).with_name('labels.json')
LOCK_PATH = Path(__file__).with_name('labels.sha256')


def label_fingerprint(labels):
    canonical = json.dumps(labels, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def class_of(relation):
    if relation.label == 'CONFLICT':
        return 'CONFLICT' if relation.comparable else 'UNRESOLVED_DIFFERENCE'
    return relation.label


def scenario_context(row, personas, cfg):
    persona = personas[row['persona_id']]
    context = make_context(persona, cfg, phase=row['phase'],
                           priorities=tuple(row.get('priorities', persona.default_priorities)),
                           as_of=row.get('as_of'))
    if row['scenario_id'] == 'sarah-expired-priorities':
        created_at = utc(row['priority_created_at'])
        context = replace(context, priorities=make_priorities(persona.default_priorities, created_at))
    elif row['scenario_id'] == 'raj-narrow-negative-feedback':
        events = tuple(FeedbackEvent(f'stress-negative-{index}', persona.persona_id,
                                     tuple(row['feedback']['topics']), False, context.as_of)
                       for index in range(5))
        context = replace(context, feedback=events)
    elif row['scenario_id'] == 'priya-feedback-decay':
        event = FeedbackEvent('stress-decay', persona.persona_id, ('thermal',), True,
                              utc(row['feedback_timestamp']))
        context = replace(context, feedback=(event,))
    return context


def evaluate(labels, cfg, messages, personas, require_approval=True):
    all_rows = (labels['baseline_scenarios'] + labels['stress_scenarios']
                + labels['proposed_relationships'])
    if require_approval and (not labels.get('ground_truth_approved')
                             or not labels.get('ground_truth_frozen')
                             or any(row.get('review_status') != 'approved' for row in all_rows)):
        raise ValueError('Formal evaluation requires human-approved frozen ground truth')
    if require_approval and (not LOCK_PATH.exists()
                             or LOCK_PATH.read_text().strip() != label_fingerprint(labels)):
        raise ValueError('Frozen ground-truth fingerprint does not match labels')
    if len(labels['baseline_scenarios']) != 20 or len(labels['stress_scenarios']) != 5:
        raise ValueError('Expected 20 baseline and five stress scenarios')
    output = {'status': 'formal' if require_approval else 'provisional — pending human review',
              'label_fingerprint': label_fingerprint(labels),
              'as_of': cfg['as_of'], 'baseline_precision_at_5': [], 'stress_precision_at_5': [],
              'prototype_pairwise_top3_jaccard': [], 'prototype_to_production': [],
              'relationship_evaluation': {}, 'faithfulness': {}}
    runs = {}
    checked = passed = 0
    for row in labels['baseline_scenarios'] + labels['stress_scenarios']:
        context = scenario_context(row, personas, cfg)
        demo = build_demo_digest(context, messages, cfg)
        result = demo.result
        actual = [item.story.story_id for item in result.digest[:5]]
        relevant = set(row['proposed_relevant_story_ids'])
        record = {'scenario_id': row['scenario_id'], 'persona_id': row['persona_id'],
                  'phase': row['phase'], 'top5': actual,
                  'relevant_in_top5': [story_id for story_id in actual if story_id in relevant],
                  'precision_at_5': sum(story_id in relevant for story_id in actual) / 5}
        destination = ('baseline_precision_at_5' if row in labels['baseline_scenarios']
                       else 'stress_precision_at_5')
        output[destination].append(record)
        if destination == 'baseline_precision_at_5':
            runs[(row['persona_id'], row['phase'])] = result
        for item in demo.items:
            checked += 1
            sources = item.ranked.story.messages + item.ranked.story.context_messages
            passed += check_faithfulness(item.summary.text, sources).ok
    values = [row['precision_at_5'] for row in output['baseline_precision_at_5']]
    output['precision_summary'] = {'macro_mean': statistics.mean(values), 'minimum': min(values),
                                   'maximum': max(values), 'below_0_60': [row['scenario_id'] for row in output['baseline_precision_at_5']
                                                                          if row['precision_at_5'] < .6]}
    for first, second in combinations(personas, 2):
        output['prototype_pairwise_top3_jaccard'].append({
            'personas': [first, second],
            'jaccard': top3_jaccard(runs[(first, 'Prototype')], runs[(second, 'Prototype')]),
            'first_top3': [x.story.story_id for x in runs[(first, 'Prototype')].digest[:3]],
            'second_top3': [x.story.story_id for x in runs[(second, 'Prototype')].digest[:3]]})
    for persona_id in personas:
        before_ids = [x.story.story_id for x in runs[(persona_id, 'Prototype')].digest[:3]]
        after_ids = [x.story.story_id for x in runs[(persona_id, 'Production')].digest[:3]]
        before, after = set(before_ids), set(after_ids)
        output['prototype_to_production'].append({'persona_id': persona_id,
                                                   'prototype_top3': before_ids,
                                                   'production_top3': after_ids,
                                                   'entered': sorted(after-before),
                                                   'exited': sorted(before-after),
                                                   'changed': before != after})
    # Pair-level evaluation uses only independently labeled pairs. Runtime may
    # preserve additional relationships in mixed groups; they are not negatives.
    full_context = make_context(personas['marcus'], cfg)
    eligible = filter_authorized_messages(messages, full_context, cfg)
    observed = {tuple(sorted(relation.source_ids)): class_of(relation)
                for story in group_and_classify(eligible, cfg) for relation in story.relationships}
    confusion = {label: {'expected': 0, 'correct': 0, 'missed': 0}
                 for label in ('DUPLICATE', 'SUPERSEDED', 'CONFLICT', 'UNRESOLVED_DIFFERENCE')}
    rows = []
    for proposal in labels['proposed_relationships']:
        pair = tuple(sorted(proposal['source_ids']))
        expected = proposal['label']
        actual = observed.get(pair, 'NONE')
        confusion[expected]['expected'] += 1
        confusion[expected]['correct' if actual == expected else 'missed'] += 1
        rows.append({'source_ids': pair, 'expected': expected, 'observed': actual,
                     'match': actual == expected})
    unresolved = [row for row in rows if row['expected'] == 'UNRESOLVED_DIFFERENCE']
    output['relationship_evaluation'] = {'labeled_pairs': rows, 'by_class': confusion,
                                         'false_scientific_conflicts_on_unresolved':
                                         sum(row['observed'] == 'CONFLICT' for row in unresolved),
                                         'unresolved_pairs_checked': len(unresolved)}
    # A deliberately unsupported identifier must fail closed to a grounded summary.
    class UnsupportedProvider:
        cache_namespace = 'eval-unsupported'
        def summarize(self, prompt):
            return 'The project uses an unsupported 999V component.'
    single = next(x.story for x in runs[('sarah', 'Prototype')].digest if x.story.label == 'SINGLE')
    fallback = summarize_story(single, provider=UnsupportedProvider())
    output['faithfulness'] = {'final_summary_count': checked, 'identifier_pass_count': passed,
                              'identifier_pass_rate': passed / checked if checked else 0,
                              'unsupported_identifier_fallback': fallback.mode == 'deterministic'
                              and fallback.fallback_reason == 'unsupported_identifier',
                              'scope': 'identifier-level factual consistency, not full semantic hallucination detection'}
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--provisional', action='store_true', help='Inspect pending proposals without claiming formal results')
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('results.json'))
    args = parser.parse_args()
    labels = json.loads(LABELS_PATH.read_text())
    cfg = load_config()
    result = evaluate(labels, cfg, load_messages(cfg=cfg), load_personas(),
                      require_approval=not args.provisional)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(f"{result['status']}: {len(result['baseline_precision_at_5'])} baseline scenarios, "
          f"macro P@5={result['precision_summary']['macro_mean']:.3f}; {args.output}")


if __name__ == '__main__':
    main()
