from dataclasses import replace
import json
import pytest
from src.config import ROOT, CHANNELS, PHASES, ROLES, TOPICS, validate_config
from src.ingestion import validate_dataset, load_messages
from src.models import utc
from src.enrichment import enrich_message
from scripts.generate_data import generate


def test_dataset_coverage(messages,personas):
    assert len(messages)==72
    assert len(personas)==5
    assert {m.channel for m in messages}==set(CHANNELS)
    assert {m.phase for m in messages}==set(PHASES)
    assert {p.role for p in personas.values()}==set(ROLES)
    assert sum(m.message_type=='chatter' for m in messages)==12
    assert all(m.timestamp.tzinfo is not None for m in messages)
    assert min(m.timestamp for m in messages)==utc('2026-09-21T10:00:00Z')
    assert max(m.timestamp for m in messages)<=utc('2026-09-27T18:00:00Z')
    assert {t for m in messages for t in m.topics}==set(TOPICS)
    assert not any('label' in row or 'story_id' in row or 'score' in row for row in generate())


def test_generator_enrichment_reproducible(messages,cfg):
    from src.models import Message
    generated=[]
    for row in generate():
        row['timestamp']=utc(row['timestamp'])
        generated.append(enrich_message(Message(**row),cfg))
    assert sorted(messages,key=lambda m:m.message_id)==generated

@pytest.mark.parametrize('mutation',['duplicate','channel','topics','naive','parent','span'])
def test_invalid_dataset_rejected(messages,mutation):
    from src.models import Identifier
    m=messages[0]
    rows=list(messages)
    if mutation=='duplicate': rows.append(m)
    elif mutation=='channel': rows[0]=replace(m,channel='unknown')
    elif mutation=='topics': rows[0]=replace(m,topics=('unknown',))
    elif mutation=='naive': rows[0]=replace(m,timestamp=m.timestamp.replace(tzinfo=None))
    elif mutation=='parent': rows[0]=replace(m,parent_id='M999')
    elif mutation=='span': rows[0]=replace(m,entities=(Identifier('voltage','24','V','24V',0,3,m.message_id),))
    with pytest.raises(ValueError): validate_dataset(rows)


def test_cached_enrichment_not_trusted(tmp_path,messages):
    rows=json.loads((ROOT/'data/slack_messages.json').read_text())
    rows[0]['topics']=['supplier'];rows[0]['message_type']='chatter';rows[0]['severity']=0
    path=tmp_path/'messages.json';path.write_text(json.dumps(rows))
    assert load_messages(path)==messages


def test_negated_blocker_is_not_blocker(messages):
    assert next(m for m in messages if m.message_id=='M034').message_type!='blocker'


def test_full_matrices_and_weights(cfg):
    validate_config(cfg)
    assert sum(cfg['weights'].values())==pytest.approx(1)
    assert len(cfg['role_topic'])==15 and len(cfg['phase_topic'])==15
    assert all(len(row)==5 for row in cfg['role_topic'].values())
    assert all(len(row)==4 for row in cfg['phase_topic'].values())

@pytest.mark.parametrize('key',['role_topic','phase_topic'])
def test_missing_matrix_row_rejected(cfg,key):
    del cfg[key]['vibration']
    with pytest.raises(ValueError): validate_config(cfg)


def test_original_matrix_transcription_exact(cfg):
    import re
    text=(ROOT/'docs/SPEC.md').read_text()
    for key,section,columns in [('role_topic','### 7.3',ROLES),('phase_topic','### 7.4',PHASES)]:
        part=text.split(section,1)[1].split('\n### ',1)[0]
        original={}
        for line in part.splitlines():
            cells=[c.strip() for c in line.strip('|').split('|')]
            if len(cells)==len(columns)+1 and re.fullmatch(r'[a-z_]+',cells[0]):
                original[cells[0]]={col:float(value) for col,value in zip(columns,cells[1:])}
        assert cfg[key]==original


def test_review_labels_have_20_plus_5_and_are_approved_and_frozen():
    labels=json.loads((ROOT/'eval/labels.json').read_text())
    assert labels['baseline_review_status']=='approved'
    assert labels['baseline_ground_truth_approved'] is True
    assert len(labels['baseline_scenarios'])==20 and len(labels['stress_scenarios'])==5
    assert len(labels['proposed_relationships'])==9
    assert all(row['review_status']=='approved' for row in labels['baseline_scenarios']+labels['stress_scenarios']+labels['proposed_relationships'])
    assert labels['review_status']=='approved'
    assert labels['ground_truth_approved'] is True
    assert labels['ground_truth_frozen'] is True


def test_phase_aware_label_sets_remain_distinct_and_approved():
    from collections import defaultdict
    labels=json.loads((ROOT/'eval/labels.json').read_text())
    by_persona=defaultdict(list)
    for row in labels['baseline_scenarios']:
        by_persona[row['persona_id']].append(row)
        assert row['business_assumption']
        assert row['review_status']=='approved'
        assert len(row['proposed_relevant_story_ids'])==len(set(row['proposed_relevant_story_ids']))
    assert len(by_persona)==5
    for rows in by_persona.values():
        assert {row['phase'] for row in rows}==set(PHASES)
        assert len({tuple(row['proposed_relevant_story_ids']) for row in rows})==4
        assert len({row['business_assumption'] for row in rows})==4
    assert labels['ground_truth_approved'] is True
