from pathlib import Path
import math
import yaml
from src.models import utc

ROOT = Path(__file__).resolve().parents[1]
ROLES = ('ME', 'EE', 'SC', 'EM', 'PM')
PHASES = ('Design', 'Prototype', 'Validation', 'Production')
TOPICS = ('vibration', 'motor', 'integration', 'tolerance', 'testing', 'thermal',
          'battery', 'firmware_if', 'supplier', 'lead_time', 'quality', 'milestone',
          'dependency', 'scope', 'design_decision')
PUBLIC_CHANNELS = ('atlas-general', 'atlas-mechanical', 'atlas-electrical',
                   'atlas-testing', 'atlas-supply-chain')
CHANNELS = PUBLIC_CHANNELS + ('atlas-leadership',)


def load_config(root=ROOT):
    cfg = {}
    for file in ('weights.yaml', 'topics.yaml', 'demo.yaml'):
        cfg.update(yaml.safe_load((root / 'config' / file).read_text()))
    validate_config(cfg)
    return cfg


def validate_config(cfg):
    expected = {'role', 'priority', 'phase', 'severity', 'recency', 'feedback'}
    if set(cfg['weights']) != expected or not math.isclose(sum(cfg['weights'].values()), 1.):
        raise ValueError('Six weights must sum to 1')
    for key, columns in [('role_topic', ROLES), ('phase_topic', PHASES)]:
        if set(cfg[key]) != set(TOPICS):
            raise ValueError('Matrix must cover all 15 topics')
        for row in cfg[key].values():
            if set(row) != set(columns) or any(not 0 <= v <= 1 for v in row.values()):
                raise ValueError('Incomplete or invalid matrix')
    if set(cfg['keywords']) != set(TOPICS):
        raise ValueError('Incomplete topic rules')
    utc(cfg['as_of'])
    if cfg['top_k'] > 5 or cfg['top_k'] < 1 or not 0 <= cfg['severity_floor']['max_items'] <= 2:
        raise ValueError('Approved digest/floor limits exceeded')
