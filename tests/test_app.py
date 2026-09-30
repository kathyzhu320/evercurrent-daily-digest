"""Streamlit AppTest exercises the actual one-page script without a browser server."""
import pytest
from streamlit.testing.v1 import AppTest


def run_app(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    return AppTest.from_file('app.py').run(timeout=30)


def assert_clean(app):
    assert not app.exception, [exception.message for exception in app.exception]


def test_default_no_key_digest_compare_and_source_traceability(monkeypatch):
    app = run_app(monkeypatch)
    assert_clean(app)
    assert [tab.label for tab in app.tabs] == ['My Digest', 'Compare personas']
    assert app.sidebar.selectbox[0].options == [
        'Sarah Chen (ME)', 'Priya Nair (EE)', 'Raj Patel (SC)',
        'Marcus Lee (EM)', 'Lena Torres (PM)']
    assert any('Sarah Chen (ME)' in item.value for item in app.caption)
    assert any(item.value == 'Raj Patel (SC)' for item in app.subheader)
    assert len(app.metric) == 5
    assert any('Conflict — sources report different values' in warning.value for warning in app.warning)
    assert any('S-M001' in item.value for item in app.markdown)
    assert any('72-hour lookback' in item.value for item in app.caption)
    assert any('Jaccard 0.00' in item.value for item in app.markdown)
    assert len(app.table) >= 5  # Six-signal breakdown is present in each card.
    assert not any('leadership' in item.value.lower() for item in app.code)
    assert all('Summary mode: deterministic' in item.value for item in app.caption
               if item.value.startswith('Summary mode:'))


def test_persona_phase_and_unresolved_wording(monkeypatch):
    app = run_app(monkeypatch)
    app.sidebar.selectbox[0].set_value('priya').run(timeout=30)
    assert_clean(app)
    assert any('Priya Nair (EE)' in item.value for item in app.caption)
    assert sum('Unresolved difference' in item.value for item in app.info) >= 2
    assert not any('contradictory' in item.value.lower() for item in app.info)
    before = [item.value for item in app.metric[:3]]
    app.sidebar.selectbox[2].set_value('Production').run(timeout=30)
    assert_clean(app)
    assert [item.value for item in app.metric[:3]] != before
    app.sidebar.selectbox[0].set_value('marcus').run(timeout=30)
    assert_clean(app)
    assert any('10/29' in item.value for item in app.code)


def test_relevant_feedback_updates_next_generation_and_is_persona_isolated(monkeypatch):
    app = run_app(monkeypatch)
    before = float(app.metric[0].value)
    assert app.session_state['feedback_sequence'] == 0
    app.button[0].click().run(timeout=30)
    assert_clean(app)
    assert app.session_state['feedback_sequence'] == 1
    assert len(app.session_state['feedback_events']['sarah']) == 1
    assert float(app.metric[0].value) > before
    app.sidebar.selectbox[0].set_value('raj').run(timeout=30)
    assert_clean(app)
    assert 'raj' not in app.session_state['feedback_events']


def test_live_toggle_without_explicit_model_uses_no_key_path(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-never-sent')
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    app = AppTest.from_file('app.py').run(timeout=30)
    app.sidebar.toggle[0].set_value(True).run(timeout=30)
    assert_clean(app)
    assert any('both OPENAI_API_KEY and OPENAI_MODEL' in item.value for item in app.sidebar.info)
    assert len(app.metric) == 5
    assert all('Summary mode: deterministic' in item.value for item in app.caption
               if item.value.startswith('Summary mode:'))


def test_all_five_persona_labels_are_consistent_in_digest_and_compare(monkeypatch):
    app = run_app(monkeypatch)
    labels = {
        'sarah': 'Sarah Chen (ME)', 'priya': 'Priya Nair (EE)',
        'raj': 'Raj Patel (SC)', 'marcus': 'Marcus Lee (EM)',
        'lena': 'Lena Torres (PM)',
    }
    app.multiselect[0].set_value(list(labels)).run(timeout=30)
    assert_clean(app)
    assert set(labels.values()) <= {item.value for item in app.subheader}
    for persona_id, label in labels.items():
        app.sidebar.selectbox[0].set_value(persona_id).run(timeout=30)
        assert_clean(app)
        assert any(item.value.startswith(label + ' ·') for item in app.caption)
        assert app.sidebar.selectbox[0].value == persona_id
