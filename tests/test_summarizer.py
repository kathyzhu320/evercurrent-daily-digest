from dataclasses import replace
import json
import os
import pytest
from src.demo import build_demo_digest
from src.personalization import make_context
from src.summarizer import (SummaryCache, OpenAIProvider, build_summary_input, cache_key,
                            deterministic_summary, provider_from_environment, source_fingerprint,
                            summarize_story)


def story_for(messages, personas, cfg, id, persona='sarah'):
    from src.pipeline import build_ranked_digest
    ranked = build_ranked_digest(make_context(personas[persona], cfg), messages, cfg).ranked
    return next(item.story for item in ranked if item.story.story_id == id)


class FakeProvider:
    cache_namespace = 'fake:v1'
    def __init__(self, answer):
        self.answer = answer
        self.calls = []
    def summarize(self, prompt):
        self.calls.append(json.loads(prompt))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_no_key_default_end_to_end(cfg, messages, personas, tmp_path, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    assert provider_from_environment(False) is None
    assert provider_from_environment(True) is None
    cache = SummaryCache(tmp_path / 'cache.json')
    out = build_demo_digest(make_context(personas['sarah'], cfg), messages, cfg, cache)
    assert len(out.items) == 5
    assert all(x.summary.mode == 'deterministic' and x.summary.text for x in out.items)
    assert all(x.ranked.story.source_message_ids for x in out.items)
    assert all(x.ranked.story.story_id == r.story.story_id for x, r in zip(out.items, out.result.digest))
    assert all(x.summary.from_cache for x in build_demo_digest(make_context(personas['sarah'], cfg), messages, cfg,
                                                               SummaryCache(cache.path)).items)


def test_optional_openai_provider_requires_key_and_is_lazy(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_MODEL', raising=False)
    with pytest.raises(ValueError):
        OpenAIProvider()
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-is-never-used')
    assert provider_from_environment(True) is None
    with pytest.raises(ValueError, match='OPENAI_MODEL'):
        OpenAIProvider()
    monkeypatch.setenv('OPENAI_MODEL', '  ')
    assert provider_from_environment(True) is None
    with pytest.raises(ValueError, match='OPENAI_MODEL'):
        OpenAIProvider()
    monkeypatch.setenv('OPENAI_MODEL', 'test-model')
    provider = provider_from_environment(True)
    assert isinstance(provider, OpenAIProvider)
    assert provider.cache_namespace.startswith('openai:')
    assert provider_from_environment(False) is None


def test_summary_cache_hit_source_change_and_namespace(cfg, messages, personas, tmp_path):
    story = story_for(messages, personas, cfg, 'S-M019')
    cache = SummaryCache(tmp_path / 'cache.json')
    first = summarize_story(story, cache)
    second = summarize_story(story, SummaryCache(cache.path))
    assert first.mode == second.mode == 'deterministic'
    assert not first.from_cache and second.from_cache
    altered = replace(story, messages=(replace(story.messages[0], text=story.messages[0].text + ' Revised fixture.'),))
    assert cache_key(altered, 'deterministic') != cache_key(story, 'deterministic')
    assert source_fingerprint(altered) != source_fingerprint(story)
    assert cache.get(altered, 'deterministic') is None
    assert cache.get(story, 'fake:v1') is None


def test_cache_acl_scope_is_source_bound(cfg, messages, personas, tmp_path):
    story = story_for(messages, personas, cfg, 'S-M014', 'marcus')
    cache = SummaryCache(tmp_path / 'cache.json')
    summarize_story(story, cache)
    partial = replace(story, messages=(story.representative,))
    assert cache.get(partial, 'deterministic') is None
    assert cache_key(partial, 'deterministic') != cache_key(story, 'deterministic')
    # A forged matching key with changed source metadata must also be rejected.
    key = cache_key(partial, 'deterministic')
    cache.entries[key] = dict(cache.entries[cache_key(story, 'deterministic')])
    assert cache.get(partial, 'deterministic') is None


def test_invalid_cached_summary_is_rejected(cfg, messages, personas, tmp_path):
    story = story_for(messages, personas, cfg, 'S-M019')
    cache = SummaryCache(tmp_path / 'cache.json')
    summarize_story(story, cache)
    key = cache_key(story, 'deterministic')
    cache.entries[key]['text'] = 'The motor mount uses 999V.'
    assert cache.get(story, 'deterministic') is None
    assert summarize_story(story, cache).text == deterministic_summary(story)

@pytest.mark.parametrize('answer,reason', [
    ('A newly invented 999V motor is ready.', 'unsupported_identifier'),
    ('', 'invalid_response'),
    ('x' * 601, 'invalid_response'),
    (RuntimeError('simulated timeout'), 'provider_error')])
def test_provider_failures_use_deterministic_fallback(cfg, messages, personas, tmp_path, answer, reason):
    story = story_for(messages, personas, cfg, 'S-M019')
    provider = FakeProvider(answer)
    cache = SummaryCache(tmp_path / 'cache.json')
    result = summarize_story(story, cache, provider)
    assert result.mode == 'deterministic'
    assert result.fallback_reason == reason
    assert result.text == deterministic_summary(story)
    assert cache.get(story, provider.cache_namespace) is None
    assert len(provider.calls) == 1


def test_valid_provider_response_cached_only_under_provider_namespace(cfg, messages, personas, tmp_path):
    story = story_for(messages, personas, cfg, 'S-M019')
    answer = 'Integration of the chassis service panel needs a fit check.'
    provider = FakeProvider(answer)
    cache = SummaryCache(tmp_path / 'cache.json')
    result = summarize_story(story, cache, provider)
    assert result.mode == 'openai' and not result.from_cache
    hit = summarize_story(story, SummaryCache(cache.path), provider)
    assert hit.mode == 'openai' and hit.from_cache
    assert len(provider.calls) == 1
    assert cache.get(story, 'deterministic') is None


def test_conflict_and_update_never_delegate_relation_judgment(cfg, messages, personas, tmp_path):
    provider = FakeProvider('Everything was correct.')
    cache = SummaryCache(tmp_path / 'cache.json')
    for id, persona in [('S-M001', 'sarah'), ('S-M009', 'priya'), ('S-M005', 'raj')]:
        story = story_for(messages, personas, cfg, id, persona)
        result = summarize_story(story, cache, provider)
        assert result.mode == 'deterministic'
        assert result.text == deterministic_summary(story)
    assert not provider.calls


def test_provider_receives_only_final_authorized_topk(cfg, messages, personas, tmp_path):
    provider = FakeProvider('Fit check needed for the chassis service panel.')
    out = build_demo_digest(make_context(personas['sarah'], cfg), messages, cfg,
                            SummaryCache(tmp_path / 'cache.json'), provider)
    allowed = set(out.result.eligible_ids)
    selected = {x.ranked.story.story_id for x in out.items}
    assert len(out.items) <= 5
    assert all(prompt['story_id'] in selected for prompt in provider.calls)
    assert all({src['id'] for src in prompt['fact_sources'] + prompt['thread_context']} <= allowed
               for prompt in provider.calls)
    assert all(src['channel'] != 'atlas-leadership' for prompt in provider.calls
               for src in prompt['fact_sources'] + prompt['thread_context'])


def test_openai_responses_adapter_parses_output_without_network(monkeypatch):
    from src import summarizer
    seen = {}
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({'output': [
                {'type': 'reasoning', 'content': []},
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Authorized fact only.'}]}]}).encode()
    def fake_open(request, timeout):
        seen['url'] = request.full_url
        seen['body'] = json.loads(request.data)
        seen['timeout'] = timeout
        seen['auth'] = request.get_header('Authorization')
        return Reply()
    monkeypatch.setattr(summarizer, 'urlopen', fake_open)
    provider = OpenAIProvider(api_key='fixture-key', model='fixture-model')
    assert provider.summarize('selected authorized source') == 'Authorized fact only.'
    assert seen['url'] == 'https://api.openai.com/v1/responses'
    assert seen['body']['input'] == 'selected authorized source'
    assert seen['body']['model'] == 'fixture-model'
    assert seen['timeout'] == 15
    assert seen['auth'] == 'Bearer fixture-key'
