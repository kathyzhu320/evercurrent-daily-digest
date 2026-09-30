from dataclasses import replace
import random
import json
from datetime import timedelta
import pytest
from src.config import PUBLIC_CHANNELS
from src.models import primitive
from src.personalization import make_context
from src.pipeline import build_ranked_digest
from scripts.run_digest import top_jaccard
from scripts.acceptance import collect_evidence


def test_A_same_public_dataset_personas(cfg,personas,messages):
    runs={id:build_ranked_digest(make_context(replace(personas[id],channels=PUBLIC_CHANNELS),cfg),messages,cfg) for id in ('sarah','raj','marcus')}
    assert len({out.eligible_ids for out in runs.values()})==1
    for x,y in [('sarah','raj'),('sarah','marcus'),('raj','marcus')]:
        assert top_jaccard(runs[x].digest,runs[y].digest)<.5
    assert 'S-M001' in {r.story.story_id for r in runs['sarah'].digest[:3]}
    assert 'S-M005' in {r.story.story_id for r in runs['raj'].digest[:3]}
    assert 'S-M037' in {r.story.story_id for r in runs['marcus'].digest[:3]}

@pytest.mark.parametrize('id',['sarah','priya','raj','marcus','lena'])
def test_B_phase_sensitivity_all_personas(cfg,personas,messages,id):
    proto=make_context(personas[id],cfg,'Prototype')
    prod=replace(proto,phase='Production')
    a,b=[build_ranked_digest(c,messages,cfg) for c in (proto,prod)]
    assert proto.priorities==prod.priorities
    assert {r.story.story_id for r in a.digest[:3]} != {r.story.story_id for r in b.digest[:3]}
    aa,bb=[{r.story.story_id:r for r in o.ranked} for o in (a,b)]
    for story in aa.keys()&bb.keys():
        assert aa[story].story.representative==bb[story].story.representative
        assert aa[story].score.final_score-bb[story].score.final_score==pytest.approx(.2*(aa[story].score.raw['phase']-bb[story].score.raw['phase']))


def test_C_priority_sensitivity(cfg,personas,messages):
    vibration=build_ranked_digest(make_context(personas['sarah'],cfg,priorities=('vibration',)),messages,cfg)
    thermal=build_ranked_digest(make_context(personas['sarah'],cfg,priorities=('thermal',)),messages,cfg)
    a,b=[{r.story.story_id:r for r in o.ranked} for o in (vibration,thermal)]
    assert a['S-M001'].score.raw['priority']==1 and b['S-M001'].score.raw['priority']==0
    assert b['S-M009'].score.raw['priority']==1 and a['S-M009'].score.raw['priority']==0
    assert b['S-M009'].score.final_score-a['S-M009'].score.final_score==pytest.approx(.25)
    assert a['S-M001'].score.final_score-b['S-M001'].score.final_score==pytest.approx(.25)
    assert {r.story.story_id for r in vibration.digest} != {r.story.story_id for r in thermal.digest}


def test_fixed_clock_and_order_reproducibility(cfg,personas,messages,monkeypatch):
    import os,time
    context=make_context(personas['sarah'],cfg)
    before=build_ranked_digest(context,messages,cfg)
    shuffled=list(messages);random.Random(7).shuffle(shuffled)
    monkeypatch.setattr(time,'time',lambda:4_000_000_000)
    after=build_ranked_digest(make_context(personas['sarah'],cfg),tuple(shuffled),cfg)
    assert primitive(before)==primitive(after)


def test_acceptance_evidence_is_reproducible_and_not_ground_truth():
    a=primitive(collect_evidence());b=primitive(collect_evidence())
    assert a==b
    assert a['label_review_status']=='pending human review'
    # The documented 0.5 reference miss remains visible, not tuned or suppressed.
    assert a['all_phase_pairwise_jaccard']['Prototype']['marcus/lena']==.5
