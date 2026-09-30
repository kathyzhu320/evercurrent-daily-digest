import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config
from src.ingestion import load_messages
from src.models import primitive

if __name__ == '__main__':
    messages = load_messages(cfg=load_config())
    (ROOT/'data/slack_messages.json').write_text(json.dumps(primitive(sorted(messages,key=lambda m:m.message_id)),indent=2)+'\n')
    print(f'Enriched {len(messages)} messages deterministically; cached fields are recomputed on load')
