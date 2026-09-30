"""Any change to approved Core Engine files requires a documented defect review."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_approved_gate1_files_match_freeze_manifest():
    manifest = json.loads((ROOT / 'docs/GATE1_FREEZE.json').read_text())
    assert manifest['status'] == 'Gate 1 PASS; Core Engine frozen'
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
