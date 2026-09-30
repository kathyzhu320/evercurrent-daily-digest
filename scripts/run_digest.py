import argparse
from pathlib import Path
import json
import sys
from itertools import combinations
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import load_config
from src.ingestion import load_messages, load_personas
from src.models import primitive
from src.personalization import make_context
from src.pipeline import build_ranked_digest


def top_jaccard(a, b):
    sa, sb = {r.story.story_id for r in a[:3]}, {r.story.story_id for r in b[:3]}
    return len(sa & sb)/len(sa | sb) if sa | sb else 1.


def compact(item):
    return {'story_id':item.story.story_id,'label':item.story.label,
            'representative_id':item.story.representative.message_id,'fact':item.story.representative.text,
            'topics':item.story.representative.topics,'category':item.category,
            'protected':item.protected,'score':primitive(item.score),
            'source_ids':item.story.source_message_ids,'differences':item.story.identifier_differences,
            'relationships':primitive(item.story.relationships)}


def main():
    parser = argparse.ArgumentParser(description='Gate 1 structured core-engine evidence; no summary/UI')
    parser.add_argument('--persona',default='sarah')
    parser.add_argument('--compare',nargs='+')
    parser.add_argument('--phase',default='Prototype')
    parser.add_argument('--priorities',nargs='*',default=None)
    parser.add_argument('--exact',nargs='*',default=[])
    parser.add_argument('--public-only',action='store_true')
    parser.add_argument('--top-n',type=int,default=None)
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--as-of',default=None)
    args=parser.parse_args()
    cfg=load_config(); messages=load_messages(cfg=cfg); personas=load_personas()
    results={}
    output={}
    for id in args.compare or [args.persona]:
        persona=personas[id]
        if args.public_only:
            from dataclasses import replace
            from src.config import PUBLIC_CHANNELS
            persona=replace(persona,channels=PUBLIC_CHANNELS)
        context=make_context(persona,cfg,args.phase,args.priorities,args.as_of,exact_terms=args.exact)
        result=build_ranked_digest(context,messages,cfg,args.top_n)
        results[id]=result.digest
        output[id]={'as_of':primitive(result.as_of),'eligible_ids':result.eligible_ids,
                    'candidate_ids':result.candidate_ids,'retrieval_reasons':result.retrieval_reasons,
                    'results':[compact(r) for r in (result.ranked if args.all else result.digest)]}
    if len(results)>1:
        output['top3_jaccard']={f'{a}/{b}':top_jaccard(results[a],results[b]) for a,b in combinations(results,2)}
    print(json.dumps(output,indent=2))

if __name__=='__main__':
    main()
