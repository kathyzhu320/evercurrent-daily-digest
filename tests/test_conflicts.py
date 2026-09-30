from dataclasses import replace
from datetime import timedelta
import pytest
from src.conflicts import group_and_classify
from src.enrichment import enrich_message
from src.models import Message,utc
from src.personalization import make_context
from src.pipeline import build_ranked_digest


def subset(messages,ids):
    return tuple(m for m in messages if m.message_id in ids)


def test_superseded_chain_and_latest_explicit_terminal(cfg,messages):
    group=group_and_classify(subset(messages,{'M005','M006','M007'}),cfg)[0]
    assert group.label=='SUPERSEDED'
    assert group.representative.message_id=='M006'
    assert {r.label for r in group.relationships}=={'SUPERSEDED','DUPLICATE'}
    assert any(r.source_ids==('M005','M006') for r in group.relationships if r.label=='SUPERSEDED')
    assert set(group.identifier_differences['lead_time'])=={'M005','M006','M007'}
    assert group.source_message_ids==('M005','M006','M007')


def test_duplicate_latest_and_no_differences(cfg,messages):
    group=group_and_classify(subset(messages,{'M046','M047'}),cfg)[0]
    assert group.label=='DUPLICATE'
    assert group.representative.message_id=='M047'
    assert group.identifier_differences=={}
    assert len(group.relationships)==1

@pytest.mark.parametrize('ids',[{'M001','M002'},{'M009','M010'},{'M012','M013'}])
def test_three_conflict_groups(cfg,messages,ids):
    group=group_and_classify(subset(messages,ids),cfg)[0]
    assert group.label=='CONFLICT' and group.identifier_differences
    assert set(group.source_message_ids)==ids


def test_comparable_and_incomparable_facts(cfg,messages):
    comparable=group_and_classify(subset(messages,{'M001','M002'}),cfg)[0]
    assert comparable.relationships[0].comparable
    different=group_and_classify(subset(messages,{'M001','M003'}),cfg)[0]
    assert not different.relationships[0].comparable
    assert 'not a scientific contradiction' in different.relationships[0].evidence

@pytest.mark.parametrize('cue',['', 'Update: ', 'now '])
def test_same_thread_author_or_vague_cue_does_not_supersede(cfg,messages,cue):
    a=next(m for m in messages if m.message_id=='M001')
    b=next(m for m in messages if m.message_id=='M002')
    b=enrich_message(replace(b,thread_id=a.thread_id,author=a.author,text=cue+b.text),cfg)
    group=group_and_classify((a,b),cfg)[0]
    assert group.label=='CONFLICT'
    assert not any(r.label=='SUPERSEDED' for r in group.relationships)


def test_update_reference_requires_same_entity_and_metric(cfg,messages):
    old=next(m for m in messages if m.message_id=='M005')
    wrong=enrich_message(replace(old,message_id='M900',timestamp=old.timestamp+timedelta(hours=1),text='Update replaces M005: Risk: Thermal result for battery BP-2400 rev B at 24V is 61 C on bench B, loaded.'),cfg)
    assert len(group_and_classify((old,wrong),cfg))==2


def test_different_parts_and_missing_part_cannot_bridge(cfg,messages):
    a=next(m for m in messages if m.message_id=='M001')
    b=enrich_message(replace(a,message_id='M901',text=a.text.replace('MM-2100','MM-2200').replace('4.2','6.8')),cfg)
    c=enrich_message(replace(a,message_id='M902',text=a.text.replace('MM-2100','').replace('4.2','8.1')),cfg)
    assert len(group_and_classify((a,b,c),cfg))==3


def test_mixed_group_keeps_all_relationships_and_sources(cfg,messages):
    a=next(m for m in messages if m.message_id=='M005')
    b=next(m for m in messages if m.message_id=='M006')
    dup=enrich_message(replace(b,message_id='M008',text='Forwarded: '+b.text.split(': ',1)[1],timestamp=b.timestamp+timedelta(minutes=1)),cfg)
    conflict=enrich_message(replace(b,message_id='M009',text=a.text.replace('12 weeks','16 weeks'),timestamp=b.timestamp+timedelta(minutes=2)),cfg)
    group=group_and_classify((a,b,dup,conflict),cfg)[0]
    assert group.label=='CONFLICT'
    assert {r.label for r in group.relationships}=={'DUPLICATE','SUPERSEDED','CONFLICT'}
    assert set(group.source_message_ids)=={'M005','M006','M008','M009'}


def test_conflict_representative_base_severity_before_time(cfg,messages):
    a=next(m for m in messages if m.message_id=='M001')
    b=next(m for m in messages if m.message_id=='M002')
    a=replace(a,message_type='blocker',severity=1)
    group=group_and_classify((a,b),cfg)[0]
    assert group.representative.message_id==a.message_id
    # Stable ID wins a complete severity/timestamp tie.
    b=replace(b,timestamp=a.timestamp,severity=1)
    assert group_and_classify((b,a),cfg)[0].representative.message_id=='M001'


def test_representatives_independent_of_persona_priority_phase(cfg,personas,messages):
    views=[]
    for id in ('sarah','raj','marcus'):
        from src.config import PUBLIC_CHANNELS
        p=replace(personas[id],channels=PUBLIC_CHANNELS)
        for phase in ('Prototype','Production'):
            out=build_ranked_digest(make_context(p,cfg,phase,priorities=()),messages,cfg)
            views.append({r.story.story_id:(r.story.representative.message_id,tuple(m.message_id for m in r.story.messages)) for r in out.ranked})
    for left,right in zip(views,views[1:]):
        assert all(left[id]==right[id] for id in left.keys()&right.keys())


def test_branched_explicit_updates_remain_unresolved(cfg,messages):
    old=next(m for m in messages if m.message_id=='M005')
    first=next(m for m in messages if m.message_id=='M006')
    second=enrich_message(replace(first,message_id='M900',timestamp=first.timestamp+timedelta(minutes=1),text=first.text.replace('20 weeks','16 weeks')),cfg)
    group=group_and_classify((old,first,second),cfg)[0]
    assert group.label=='CONFLICT'
    assert sum(r.label=='SUPERSEDED' for r in group.relationships)==2
    assert any(r.label=='CONFLICT' and set(r.source_ids)=={'M006','M900'} for r in group.relationships)


def test_changed_ambient_temperature_not_comparable(cfg,messages):
    a=next(m for m in messages if m.message_id=='M001')
    b=next(m for m in messages if m.message_id=='M002')
    a=enrich_message(replace(a,text=a.text+' Ambient temperature 25 C.'),cfg)
    b=enrich_message(replace(b,text=b.text+' Ambient temperature 35 C.'),cfg)
    group=group_and_classify((a,b),cfg)[0]
    assert group.label=='CONFLICT'
    assert not any(r.comparable for r in group.relationships)


def test_thread_does_not_merge_unrelated_facts(cfg,messages):
    a=next(m for m in messages if m.message_id=='M001')
    b=next(m for m in messages if m.message_id=='M005')
    b=replace(b,thread_id=a.thread_id)
    assert len(group_and_classify((a,b),cfg))==2
