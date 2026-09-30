import hashlib
import json
from pathlib import Path


def test_human_accepted_demo_behavior_is_frozen():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'docs/GATE2_FREEZE.json').read_text())
    assert manifest['gate_1'] == 'PASS' and manifest['gate_2'] == 'PASS (human accepted)'
    for relative_path, expected in manifest['sha256'].items():
        assert hashlib.sha256((root / relative_path).read_bytes()).hexdigest() == expected, relative_path
