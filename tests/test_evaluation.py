import json
import pytest
from eval.evaluate import evaluate


def test_unapproved_labels_cannot_produce_formal_evaluation(cfg, messages, personas):
    labels = json.load(open('eval/labels.json'))
    labels['ground_truth_approved'] = False
    with pytest.raises(ValueError, match='human-approved frozen'):
        evaluate(labels, cfg, messages, personas)


def test_provisional_evaluation_reports_all_scenarios_without_tuning(cfg, messages, personas):
    labels = json.load(open('eval/labels.json'))
    labels['ground_truth_approved'] = False
    result = evaluate(labels, cfg, messages, personas, require_approval=False)
    assert result['status'].startswith('provisional')
    assert len(result['baseline_precision_at_5']) == 20
    assert len(result['stress_precision_at_5']) == 5
    assert len(result['prototype_pairwise_top3_jaccard']) == 10
    assert all(row['changed'] for row in result['prototype_to_production'])
    assert result['relationship_evaluation']['false_scientific_conflicts_on_unresolved'] == 0
    assert result['relationship_evaluation']['unresolved_pairs_checked'] == 3
    assert result['faithfulness']['unsupported_identifier_fallback']


def test_approved_frozen_labels_produce_formal_evaluation(cfg, messages, personas):
    labels = json.load(open('eval/labels.json'))
    result = evaluate(labels, cfg, messages, personas)
    assert result['status'] == 'formal'
    assert len(result['baseline_precision_at_5']) == 20
    assert len(result['stress_precision_at_5']) == 5
    assert result['precision_summary']['macro_mean'] == 0.65
