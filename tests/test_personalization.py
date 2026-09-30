from dataclasses import replace
from datetime import timedelta
import pytest
from src.models import FeedbackEvent
from src.personalization import make_context,make_priorities,active_priorities,decayed_preferences,apply_feedback


def test_priority_ttl_and_expiration(cfg,personas):
    ctx=make_context(personas['sarah'],cfg)
    assert all(p.expires_at-p.created_at==timedelta(days=7) for p in ctx.priorities)
    assert active_priorities(replace(ctx,as_of=ctx.as_of+timedelta(days=7)))==()
    assert active_priorities(replace(ctx,as_of=ctx.as_of-timedelta(seconds=1)))==()

@pytest.mark.parametrize('relevant,expected',[(True,.2),(False,-.2)])
def test_feedback_step_and_half_life(cfg,personas,relevant,expected):
    ctx=make_context(personas['sarah'],cfg)
    e=FeedbackEvent('E1','sarah',('vibration','motor'),relevant,ctx.as_of)
    prefs=decayed_preferences((e,),'sarah',ctx.as_of,cfg)
    assert prefs==dict(vibration=expected,motor=expected)
    assert decayed_preferences((e,),'sarah',ctx.as_of+timedelta(days=7),cfg)['vibration']==pytest.approx(expected/2)
    assert decayed_preferences((e,),'raj',ctx.as_of,cfg)=={}
    assert decayed_preferences((e,),'sarah',ctx.as_of-timedelta(seconds=1),cfg)=={}

@pytest.mark.parametrize('relevant,expected',[(True,1.),(False,-1.)])
def test_clip(cfg,personas,relevant,expected):
    ctx=make_context(personas['sarah'],cfg)
    events=tuple(FeedbackEvent(f'E{i}','sarah',('vibration',),relevant,ctx.as_of) for i in range(8))
    assert decayed_preferences(events,'sarah',ctx.as_of,cfg)['vibration']==expected


def test_decay_before_next_feedback_update(cfg,personas):
    ctx=make_context(personas['sarah'],cfg)
    a=FeedbackEvent('A','sarah',('vibration',),True,ctx.as_of)
    b=FeedbackEvent('B','sarah',('vibration',),True,ctx.as_of+timedelta(days=7))
    assert decayed_preferences((a,b),'sarah',b.timestamp,cfg)['vibration']==pytest.approx(.3)


def test_feedback_idempotence(cfg,personas):
    ctx=make_context(personas['sarah'],cfg)
    event=FeedbackEvent('A','sarah',('vibration',),True,ctx.as_of)
    events=apply_feedback((),event)
    assert apply_feedback(events,event)==events
    assert decayed_preferences(events+events,'sarah',ctx.as_of,cfg)['vibration']==pytest.approx(.2)
    with pytest.raises(ValueError): apply_feedback(events,replace(event,relevant=False))
