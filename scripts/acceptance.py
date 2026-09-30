"""A–F CLI evidence, not evaluation against unreviewed ground truth."""
from pathlib import Path
import sys
import json
from dataclasses import replace
from datetime import timedelta
from itertools import combinations
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, PUBLIC_CHANNELS, load_config
from src.models import Message, FeedbackEvent, primitive
from src.enrichment import enrich_message
from src.ingestion import load_messages, load_personas
from src.personalization import make_context, make_priorities
from src.pipeline import build_ranked_digest
from src.retrieval import filter_authorized_messages, retrieve_candidates
from src.ranking import select_top_k
from scripts.run_digest import compact, top_jaccard


def floor_fixture(cfg, persona):
    context = make_context(persona, cfg, priorities=('integration',))
    messages = []
    for i in range(6):
        raw = Message(f'F{i:03}', 'atlas-mechanical', context.as_of-timedelta(hours=1), 'Alex', 'ME',
                      f'FT{i:03}', f'Integration update: chassis assembly fit ready for station {i}.')
        messages.append(enrich_message(raw, cfg))
    risk = Message('F900', 'atlas-supply-chain', context.as_of-timedelta(hours=60), 'Raj', 'SC',
                   'FT900', 'Risk: Supplier allocation remains uncertain; purchasing needs confirmation.')
    messages.append(enrich_message(risk, cfg))
    feedback = tuple(FeedbackEvent(f'negative-{i}',persona.persona_id,('supplier',),False,context.as_of) for i in range(5))
    return tuple(messages), replace(context,feedback=feedback)


def collect_evidence():
    cfg=load_config(); ms=load_messages(cfg=cfg); ps=load_personas()
    evidence={'as_of':cfg['as_of'],'label_review_status':'pending human review',
              'evaluation_claim':'Acceptance mechanics only. No P@5/ground-truth evaluation claimed.'}
    publics={id:replace(ps[id],channels=PUBLIC_CHANNELS) for id in ps}
    a={id:build_ranked_digest(make_context(publics[id],cfg),ms,cfg) for id in ('sarah','raj','marcus')}
    evidence['A_public_default_priorities']={id:[compact(r) for r in out.digest] for id,out in a.items()}
    evidence['A_top3_jaccard']={f'{x}/{y}':top_jaccard(a[x].digest,a[y].digest) for x,y in combinations(a,2)}
    control={id:build_ranked_digest(make_context(publics[id],cfg,priorities=()),ms,cfg) for id in a}
    evidence['A_public_aligned_empty_priorities_control']={id:[compact(r) for r in out.digest] for id,out in control.items()}
    evidence['B_phase']={}
    evidence['all_phase_pairwise_jaccard']={}
    for phase in ('Design','Prototype','Validation','Production'):
        runs={id:build_ranked_digest(make_context(p,cfg,phase),ms,cfg) for id,p in ps.items()}
        evidence['all_phase_pairwise_jaccard'][phase]={f'{x}/{y}':top_jaccard(runs[x].digest,runs[y].digest) for x,y in combinations(ps,2)}
    for id,p in ps.items():
        before=build_ranked_digest(make_context(p,cfg,'Prototype'),ms,cfg)
        after=build_ranked_digest(make_context(p,cfg,'Production'),ms,cfg)
        evidence['B_phase'][id]={'Prototype':[compact(r) for r in before.digest], 'Production':[compact(r) for r in after.digest],
                               'top3_changed':{r.story.story_id for r in before.digest[:3]} != {r.story.story_id for r in after.digest[:3]}}
    evidence['C_priorities']={}
    for priority in ('vibration','thermal'):
        result=build_ranked_digest(make_context(ps['sarah'],cfg,priorities=(priority,)),ms,cfg)
        evidence['C_priorities'][priority]={'digest':[compact(r) for r in result.digest],
                                          'all_ranked':[compact(r) for r in result.ranked]}
    result=build_ranked_digest(make_context(ps['marcus'],cfg),ms,cfg)
    evidence['D_relationships']=[compact(r) for r in result.ranked if r.story.label!='SINGLE']
    # Include true cross-channel duplicate even if candidate pruning omitted it for Marcus.
    from src.conflicts import group_and_classify
    all_public=filter_authorized_messages(ms,make_context(publics['sarah'],cfg),cfg)
    evidence['D_all_public_relationships']=primitive([s for s in group_and_classify(all_public,cfg) if s.label!='SINGLE'])
    private={m.message_id for m in ms if m.channel=='atlas-leadership'}
    evidence['E_acl']={}
    for id,p in ps.items():
        out=build_ranked_digest(make_context(p,cfg),ms,cfg)
        evidence['E_acl'][id]={'eligible_private_ids':sorted(private & set(out.eligible_ids)),
                               'candidate_private_ids':sorted(private & set(out.candidate_ids)),
                               'story_private_ids':sorted(private & {sid for r in out.ranked for sid in r.story.source_message_ids})}
    fixture,ctx=floor_fixture(cfg,ps['sarah'])
    eligible=filter_authorized_messages(fixture,ctx,cfg)
    ordinary,reasons=retrieve_candidates(eligible,ctx,cfg,top_n=1)
    out=build_ranked_digest(ctx,fixture,cfg,top_n=1)
    normal=select_top_k(out.ranked,cfg,use_floor=False)
    evidence['F_floor']={'fixture_messages':primitive(fixture),'negative_feedback':primitive(ctx.feedback),
                         'ordinary_candidate_ids':[m.message_id for m in ordinary],
                         'ordinary_top5':[compact(r) for r in normal],
                         'protected_digest':[compact(r) for r in out.digest],
                         'retrieval_reasons':out.retrieval_reasons}
    return evidence


def main():
    output=collect_evidence()
    if len(sys.argv)>1:
        path=Path(sys.argv[1]);path.write_text(json.dumps(primitive(output),indent=2)+'\n')
        print(f'A–F evidence written: {path}; labels pending human review')
    else:
        print(json.dumps(primitive(output),indent=2))

if __name__=='__main__':
    main()
