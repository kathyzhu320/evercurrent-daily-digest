"""Validate reproducibility metadata; TF-IDF vectors are fit only after ACL at runtime."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT
from src.ingestion import load_messages
from src.retrieval import index_manifest

if __name__ == '__main__':
    manifest = index_manifest(load_messages())
    (ROOT/'data/index_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('TF-IDF manifest written; no embeddings/model/vector infrastructure')
