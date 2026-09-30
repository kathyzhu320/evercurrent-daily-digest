import pytest
from src.config import load_config
from src.ingestion import load_messages, load_personas

@pytest.fixture
def cfg():
    return load_config()

@pytest.fixture
def messages(cfg):
    return load_messages(cfg=cfg)

@pytest.fixture
def personas():
    return load_personas()
