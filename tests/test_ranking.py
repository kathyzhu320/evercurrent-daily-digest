from dataclasses import replace
from datetime import timedelta
import pytest
from src.models import Story, FeedbackEvent
from src.personalization import make_context
from src.ranking import score_story,select_top_k,rank_key
from src.pipeline import build_ranked_digest
from scripts.acceptance import floor_fixture


def singleton(message):
    return Story('S-'+message.message_id,(message,),message,'SINGLE',(),{})


def test_corrected_worked_example(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    template=messages[0]
    a=replace(template,message_id='A',timestamp=ctx.as_of-timedelta(hours=10),topics=('vibration','motor','testing'),message_type='risk',severity=.8,affects=('motor_mount',),reply_count=0)
    b=replace(template,message_id='B',timestamp=ctx.as_of-timedelta(hours=30),topics=('lead_time','supplier'),message_type='risk',severity=.8,affects=('motor_driver','bom'),reply_count=0)
    expected={'sarah':(.9315536561,.3848419777),'raj':(.5315536561,.8098419777)}
    for id,(ea,eb) in expected.items():
        context=make_context(personas[id],cfg)
        sa,sb=score_story(singleton(a),context,cfg),score_story(singleton(b),context,cfg)
        assert sa.score.final_score==pytest.approx(ea,abs=1e-8)
        assert sb.score.final_score==pytest.approx(eb,abs=1e-8)
        assert sa.score.raw['phase']==1.0
        prod=replace(context,phase='Production')
        assert score_story(singleton(a),prod,cfg).score.final_score-sa.score.final_score==pytest.approx(-.1)
        assert score_story(singleton(b),prod,cfg).score.final_score-sb.score.final_score==pytest.approx(.1)


def test_owner_override_and_category(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    m=replace(messages[0],timestamp=ctx.as_of,topics=('battery',),affects=('chassis',),message_type='risk',severity=.8)
    score=score_story(singleton(m),ctx,cfg)
    assert score.score.raw['role']==.9
    assert score.category=='Action Required'
    assert score.score.owns_affects==('chassis',)

@pytest.mark.parametrize('count,kind,base,expected',[(0,'risk',.8,.8),(1,'risk',.8,.825),(4,'risk',.8,.9),(10,'risk',.8,.9),(4,'blocker',1.,1.)])
def test_severity_attention_cap(cfg,personas,messages,count,kind,base,expected):
    ctx=make_context(personas['sarah'],cfg)
    m=replace(messages[0],timestamp=ctx.as_of,reply_count=count,message_type=kind,severity=base,reactions=999)
    assert score_story(singleton(m),ctx,cfg).score.raw['severity']==pytest.approx(expected)

@pytest.mark.parametrize('age,expected',[(0,1.),(48,.5),(72,.5**1.5)])
def test_recency_half_life(cfg,personas,messages,age,expected):
    ctx=make_context(personas['sarah'],cfg)
    m=replace(messages[0],timestamp=ctx.as_of-timedelta(hours=age))
    assert score_story(singleton(m),ctx,cfg).score.raw['recency']==pytest.approx(expected)

@pytest.mark.parametrize('topics,priorities,expected',[(('vibration','thermal'),('vibration',),1.),(('vibration','thermal'),('thermal',),.6),(('vibration','thermal'),('supplier',),0.)])
def test_primary_secondary_priority(cfg,personas,messages,topics,priorities,expected):
    ctx=make_context(personas['sarah'],cfg,priorities=priorities)
    m=replace(messages[0],timestamp=ctx.as_of,topics=topics)
    assert score_story(singleton(m),ctx,cfg).score.raw['priority']==expected
    future=replace(ctx,as_of=ctx.as_of+timedelta(days=7))
    assert score_story(singleton(m),future,cfg).score.raw['priority']==0


def test_feedback_neutral_and_score_effect(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    story=singleton(replace(messages[0],timestamp=ctx.as_of))
    before=score_story(story,ctx,cfg)
    assert before.score.raw['feedback']==.5
    event=FeedbackEvent('X','sarah',story.representative.topics,True,ctx.as_of)
    after=score_story(story,replace(ctx,feedback=(event,)),cfg)
    assert after.score.raw['feedback']==pytest.approx(.6)
    assert after.score.final_score-before.score.final_score==pytest.approx(.005)
    decayed=score_story(story,replace(ctx,as_of=ctx.as_of+timedelta(days=7),feedback=(event,)),cfg)
    assert decayed.score.raw['feedback']==pytest.approx(.55)


def test_stable_tie_breaking(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    m=replace(messages[0],timestamp=ctx.as_of)
    items=[score_story(singleton(replace(m,message_id=id)),ctx,cfg) for id in ('B','A','C')]
    assert [r.story.story_id for r in select_top_k(items,cfg)]==['S-A','S-B','S-C']


def test_floor_survives_pruning_and_negative_feedback(cfg,personas):
    from src.retrieval import filter_authorized_messages,retrieve_candidates
    ms,ctx=floor_fixture(cfg,personas['sarah'])
    eligible=filter_authorized_messages(ms,ctx,cfg)
    ordinary,_=retrieve_candidates(eligible,ctx,cfg,top_n=1)
    assert 'F900' not in {m.message_id for m in ordinary}
    out=build_ranked_digest(ctx,ms,cfg,top_n=1)
    assert 'S-F900' not in {r.story.story_id for r in select_top_k(out.ranked,cfg,use_floor=False)}
    risk=next(r for r in out.digest if r.story.story_id=='S-F900')
    assert risk.protected and risk.score.raw['role']>=.3
    assert risk.score.raw['feedback']==pytest.approx(0)
    assert len(out.digest)==5 and sum(r.protected for r in out.digest)<=2
    assert len({r.story.story_id for r in out.digest})==len(out.digest)


def test_floor_at_most_two_when_many_risks(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    risk=replace(messages[0],timestamp=ctx.as_of,topics=('vibration',),affects=(),message_type='risk',severity=.8,reply_count=0)
    items=[score_story(singleton(replace(risk,message_id=f'R{i}')),ctx,cfg) for i in range(7)]
    digest=select_top_k(items,cfg)
    assert len(digest)==5
    assert sum(r.protected for r in digest)==2
    assert {r.story.story_id for r in digest if r.protected}=={'S-R0','S-R1'}


def test_floor_role_threshold(cfg,personas,messages):
    ctx=make_context(personas['raj'],cfg)
    risk=replace(messages[0],timestamp=ctx.as_of,topics=('vibration',),affects=(),message_type='risk',severity=.8)
    assert not score_story(singleton(risk),ctx,cfg).score.floor_eligible
    assert score_story(singleton(replace(risk,topics=('design_decision',))),ctx,cfg).score.floor_eligible


def test_score_contributions_and_range(cfg,personas,messages):
    for p in personas.values():
        result=build_ranked_digest(make_context(p,cfg),messages,cfg)
        for r in result.ranked:
            assert sum(r.score.weighted.values())==pytest.approx(r.score.final_score)
            assert all(0<=v<=1 for v in r.score.raw.values())
            assert 0<=r.score.final_score<=1


def test_future_score_rejected(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    with pytest.raises(ValueError):
        score_story(singleton(replace(messages[0],timestamp=ctx.as_of+timedelta(seconds=1))),ctx,cfg)


def test_action_required_precedes_risk_category(cfg,personas,messages):
    result=build_ranked_digest(make_context(personas['sarah'],cfg),messages,cfg)
    assert all(r.category=='Action Required' for r in result.digest if r.protected and r.score.owns_affects)


def test_all_ranked_protection_flags_match_final_digest(cfg,personas,messages):
    out=build_ranked_digest(make_context(personas['sarah'],cfg),messages,cfg)
    protected={r.story.story_id for r in out.digest if r.protected}
    assert protected=={r.story.story_id for r in out.ranked if r.protected}
    assert not any(r.protected for r in select_top_k(out.ranked,cfg,use_floor=False))
