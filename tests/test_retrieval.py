from dataclasses import replace
from datetime import timedelta
import json
import pytest
from src.config import ROOT
from src.personalization import make_context
from src.retrieval import filter_authorized_messages,retrieve_candidates,index_manifest,validate_index_manifest
from src.pipeline import build_ranked_digest
from src.enrichment import enrich_message
from src.ingestion import count_authorized_replies

@pytest.mark.parametrize('id,allowed',[('sarah',False),('priya',False),('raj',False),('marcus',True),('lena',True)])
def test_acl_all_stages(cfg,personas,messages,id,allowed,monkeypatch):
    import src.pipeline as pipeline
    ctx=make_context(personas[id],cfg)
    seen=[]
    real_retrieve=pipeline.retrieve_candidates
    real_group=pipeline.group_and_classify
    def retrieve(eligible,*args,**kwargs):
        seen.extend(eligible)
        assert all(m.channel in ctx.persona.channels for m in eligible)
        return real_retrieve(eligible,*args,**kwargs)
    def group(candidates,*args,**kwargs):
        assert all(m.channel in ctx.persona.channels for m in candidates)
        assert all(m.channel in ctx.persona.channels for m in kwargs.get('similarity_messages',()))
        return real_group(candidates,*args,**kwargs)
    monkeypatch.setattr(pipeline,'retrieve_candidates',retrieve)
    monkeypatch.setattr(pipeline,'group_and_classify',group)
    out=build_ranked_digest(ctx,messages,cfg)
    private={m.message_id for m in messages if m.channel=='atlas-leadership'}
    assert bool(private & set(out.eligible_ids))==allowed
    assert bool(private & set(out.candidate_ids))==allowed
    sources={id for r in out.ranked for id in r.story.source_message_ids}
    assert bool(private & sources)==allowed
    if not allowed:
        assert not private & set(out.retrieval_reasons)
        assert all(m.channel!='atlas-leadership' for r in out.ranked for m in r.story.messages+r.story.context_messages)

@pytest.mark.parametrize('age,included',[(0,True),(24,True),(48,True),(72,True),(72+1/3600,False),(-1/3600,False)])
def test_72h_boundary_and_future(cfg,personas,messages,age,included):
    ctx=make_context(personas['sarah'],cfg)
    m=replace(messages[-1],timestamp=ctx.as_of-timedelta(hours=age),message_type='update')
    assert bool(filter_authorized_messages((m,),ctx,cfg))==included


def test_project_and_chatter_filter(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    assert not filter_authorized_messages(tuple(m for m in messages if m.message_type=='chatter'),ctx,cfg)
    m=replace(messages[3],project='Other')
    assert not filter_authorized_messages((m,),ctx,cfg)


def test_exact_identifier_union_and_token_boundary(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg,priorities=(),exact_terms=('24 V',))
    template=replace(messages[3],timestamp=ctx.as_of,message_id='I1',text='Voltage reference is 24V.',parent_id=None)
    a=enrich_message(template,cfg)
    b=enrich_message(replace(template,message_id='I2',thread_id='INDEPENDENT',text='Voltage reference is 124V.'),cfg)
    eligible=filter_authorized_messages((a,b),ctx,cfg)
    candidates,reasons=retrieve_candidates(eligible,ctx,cfg,top_n=0)
    assert {m.message_id for m in candidates}=={'I1'}
    assert 'identifier_union' in reasons['I1']


def test_priority_union_outside_topn(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg,priorities=('vibration',))
    eligible=filter_authorized_messages(messages,ctx,cfg)
    candidates,reasons=retrieve_candidates(eligible,ctx,cfg,top_n=0)
    assert {'M001','M002','M003','M004'} <= {m.message_id for m in candidates}
    assert 'priority_keyword' in reasons['M001']


def test_index_alignment_and_content(cfg,messages):
    manifest=index_manifest(messages)
    validate_index_manifest(messages,manifest)
    assert manifest==json.loads((ROOT/'data/index_manifest.json').read_text())
    with pytest.raises(ValueError): validate_index_manifest(messages[::-1],manifest)
    with pytest.raises(ValueError): validate_index_manifest((replace(messages[0],text='changed'),)+messages[1:],manifest)


def test_authorized_thread_expansion_and_reply_count(cfg,personas,messages):
    ctx=make_context(personas['sarah'],cfg)
    pub=replace(messages[3],message_id='P',channel='atlas-general',timestamp=ctx.as_of,thread_id='SHARED',parent_id=None,reply_count=99)
    private=replace(pub,message_id='H',channel='atlas-leadership',parent_id='P')
    old=replace(pub,message_id='O',parent_id='P',timestamp=ctx.as_of-timedelta(hours=73))
    new=replace(pub,message_id='R',parent_id='P',timestamp=ctx.as_of)
    eligible=count_authorized_replies(filter_authorized_messages((pub,private,old,new),ctx,cfg))
    assert {m.message_id for m in eligible}=={'P','R'}
    assert all(m.reply_count==1 for m in eligible)
    out=build_ranked_digest(ctx,(pub,private,old,new),cfg)
    assert all(set(r.story.source_message_ids)<={'P','R'} for r in out.ranked)


def test_empty_corpus(cfg,personas):
    out=build_ranked_digest(make_context(personas['sarah'],cfg),(),cfg)
    assert not out.digest and not out.ranked
