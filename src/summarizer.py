"""Summary-only providers, authorized-source cache, and deterministic fallback."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import hashlib
import json
import os
import re
import tempfile
from urllib.request import Request, urlopen
from src.config import ROOT
from src.faithfulness import check_faithfulness
from src.models import Story, primitive
from src.presentation import story_marker

PROMPT_VERSION = 'gate2-v2'
CACHE_PATH = ROOT / 'data/summaries_cache.json'


class SummaryProvider(Protocol):
    cache_namespace: str
    def summarize(self, prompt: str) -> str: ...


class OpenAIProvider:
    """Optional Responses API adapter. No SDK install or API call on the default path."""
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = (api_key or os.environ.get('OPENAI_API_KEY') or '').strip()
        if not self._api_key:
            raise ValueError('OPENAI_API_KEY is not configured')
        self.model = (model or os.environ.get('OPENAI_MODEL') or '').strip()
        if not self.model:
            raise ValueError('OPENAI_MODEL is not configured')
        self.cache_namespace = f'openai:{self.model}'

    def summarize(self, prompt: str) -> str:
        body = json.dumps({
            'model': self.model,
            'instructions': ('Summarize only the supplied authorized Slack facts in one concise '
                             'sentence. Never decide ranking, permissions, or which conflicting '
                             'source is correct. Preserve engineering numbers, units, dates, '
                             'versions, part IDs, and uncertainty. Do not invent facts.'),
            'input': prompt,
        }).encode()
        request = Request('https://api.openai.com/v1/responses', data=body,
                          headers={'Authorization': 'Bearer ' + self._api_key,
                                   'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=15) as response:
            data = json.load(response)
        return ' '.join(part.get('text', '') for item in data.get('output', [])
                        if item.get('type') == 'message' and item.get('role') == 'assistant'
                        for part in item.get('content', []) if part.get('type') == 'output_text').strip()


def provider_from_environment(live: bool) -> SummaryProvider | None:
    return (OpenAIProvider() if live and (os.environ.get('OPENAI_API_KEY') or '').strip()
            and (os.environ.get('OPENAI_MODEL') or '').strip() else None)


@dataclass(frozen=True)
class SummaryResult:
    text: str
    mode: str
    from_cache: bool = False
    fallback_reason: str = ''


def _authorized_sources(story: Story):
    return tuple(sorted({m.message_id: m for m in story.messages + story.context_messages}.values(),
                        key=lambda m: m.message_id))


def source_fingerprint(story: Story) -> str:
    data = {'story_id': story.story_id, 'label': story.label,
            'representative_id': story.representative.message_id,
            'relationships': primitive(story.relationships),
            'sources': primitive(_authorized_sources(story))}
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def cache_key(story: Story, namespace: str) -> str:
    data = f'{PROMPT_VERSION}|{namespace}|{source_fingerprint(story)}'
    return hashlib.sha256(data.encode()).hexdigest()


class SummaryCache:
    def __init__(self, path: Path = CACHE_PATH):
        self.path = Path(path)
        try:
            loaded = json.loads(self.path.read_text())
            self.entries = loaded if isinstance(loaded, dict) else {}
        except (FileNotFoundError, ValueError):
            self.entries = {}

    def get(self, story: Story, namespace: str) -> SummaryResult | None:
        key = cache_key(story, namespace)
        entry = self.entries.get(key)
        sources = tuple(m.message_id for m in _authorized_sources(story))
        if not isinstance(entry, dict) or entry.get('story_id') != story.story_id:
            return None
        if entry.get('source_ids') != list(sources) or entry.get('source_fingerprint') != source_fingerprint(story):
            return None
        if entry.get('namespace') != namespace or entry.get('prompt_version') != PROMPT_VERSION:
            return None
        if namespace == 'deterministic' and entry.get('mode') != 'deterministic':
            return None
        text = entry.get('text')
        if not valid_summary(text) or not check_faithfulness(text, _authorized_sources(story)).ok:
            return None
        return SummaryResult(text, entry.get('mode', 'deterministic'), True)

    def put(self, story: Story, namespace: str, result: SummaryResult):
        if not valid_summary(result.text) or not check_faithfulness(result.text, _authorized_sources(story)).ok:
            raise ValueError('Cannot cache invalid or unsupported summary')
        key = cache_key(story, namespace)
        self.entries[key] = {'story_id': story.story_id,
                             'source_ids': [m.message_id for m in _authorized_sources(story)],
                             'source_fingerprint': source_fingerprint(story),
                             'prompt_version': PROMPT_VERSION, 'namespace': namespace,
                             'mode': result.mode, 'text': result.text}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=self.path.parent, prefix='.summaries-',
                                         suffix='.json', delete=False) as handle:
            json.dump(self.entries, handle, indent=2, sort_keys=True)
            handle.write('\n')
            temp_path = Path(handle.name)
        temp_path.replace(self.path)


def valid_summary(text) -> bool:
    return isinstance(text, str) and bool(text.strip()) and len(text.strip()) <= 600 and not text.lstrip().startswith(('{', '['))


def build_summary_input(story: Story) -> str:
    # The caller must pass a story from the final authorized Top-K. No global corpus.
    payload = {'story_id': story.story_id, 'presentation_marker': story_marker(story),
               'representative_id': story.representative.message_id,
               'fact_sources': [{'id': m.message_id, 'channel': m.channel,
                                 'timestamp_utc': primitive(m.timestamp), 'text': m.text}
                                for m in story.messages],
               'thread_context': [{'id': m.message_id, 'channel': m.channel,
                                   'timestamp_utc': primitive(m.timestamp), 'text': m.text}
                                  for m in story.context_messages],
               'relationship_evidence': primitive(story.relationships)}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _first_sentence(text: str) -> str:
    text = re.sub(r'^(?:Forwarded:\s*|FYI:\s*|Update replaces M\d+:\s*|Correction corrects M\d+:\s*)+', '', text, flags=re.I)
    return text.split('. ', 1)[0].rstrip(' .') + '.'


def deterministic_summary(story: Story) -> str:
    fact = _first_sentence(story.representative.text)
    if story.label in ('SINGLE', 'DUPLICATE'):
        return fact
    if story.label == 'CONFLICT':
        comparable = [r for r in story.relationships if r.label == 'CONFLICT' and r.comparable]
        if comparable:
            pair = comparable[0]
            measured = pair.differences.get('vibration') or next(iter(pair.differences.values()), {})
            details = '; '.join(f'{source_id} ' + ', '.join(value + (' ' + unit if unit else '')
                                                       for value, unit in values)
                                for source_id, values in measured.items())
            mixed = any(r.label == 'CONFLICT' and not r.comparable for r in story.relationships)
            text = f'Conflict — sources report different values. {fact} Same-condition measurements: {details}.'
            if mixed:
                text += ' Other source comparisons have different or unverified test conditions.'
            return text
    differences = []
    for kind, by_source in story.identifier_differences.items():
        seen = []
        for source_id, values in by_source.items():
            for value, unit in values:
                display = value + (' ' + unit if unit else '')
                if display not in seen:
                    seen.append(display)
        if len(seen) > 1:
            connector = ' → ' if story.label == 'SUPERSEDED' else ' vs '
            differences.append(f'{kind}: ' + connector.join(seen))
    suffix = '; '.join(differences)
    marker = story_marker(story)
    text = f'{marker}. {fact}' + (f' Source values: {suffix}.' if suffix else '')
    return text[:600] if len(text) > 600 else text


def summarize_story(story: Story, cache: SummaryCache | None = None,
                    provider: SummaryProvider | None = None) -> SummaryResult:
    # Conflict and explicit-update facts are rendered deterministically so a model
    # cannot silently choose a winner or collapse the superseded chain.
    use_provider = provider is not None and story.label in ('SINGLE', 'DUPLICATE')
    namespace = provider.cache_namespace if use_provider else 'deterministic'
    if cache and (hit := cache.get(story, namespace)):
        return hit
    fallback = deterministic_summary(story)
    if use_provider:
        try:
            candidate = provider.summarize(build_summary_input(story)).strip()
            if not valid_summary(candidate):
                reason = 'invalid_response'
            elif not check_faithfulness(candidate, _authorized_sources(story)).ok:
                reason = 'unsupported_identifier'
            else:
                result = SummaryResult(candidate, 'openai')
                if cache:
                    cache.put(story, namespace, result)
                return result
        except Exception:
            reason = 'provider_error'
        result = SummaryResult(fallback, 'deterministic', False, reason)
    else:
        result = SummaryResult(fallback, 'deterministic', False,
                               'relation_guard' if provider is not None else 'no_key_or_live_disabled')
    # A bad provider answer never enters the provider cache; deterministic fallback
    # has its own namespace and is safe to precompute/reuse.
    if cache:
        cached = cache.get(story, 'deterministic')
        if cached:
            return SummaryResult(cached.text, cached.mode, True, result.fallback_reason)
        cache.put(story, 'deterministic', SummaryResult(fallback, 'deterministic'))
    return result
