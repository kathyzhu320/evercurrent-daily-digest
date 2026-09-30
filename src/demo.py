"""Gate 2 composition: approved Top-K in, grounded presentation summaries out."""
from dataclasses import dataclass
from src.models import DigestResult, FeedbackEvent, RankedStory, UserContext
from src.personalization import apply_feedback
from src.pipeline import build_ranked_digest
from src.summarizer import SummaryCache, SummaryProvider, SummaryResult, summarize_story


@dataclass(frozen=True)
class DemoItem:
    ranked: RankedStory
    summary: SummaryResult


@dataclass(frozen=True)
class DemoDigest:
    result: DigestResult
    items: tuple[DemoItem, ...]


def build_demo_digest(context: UserContext, messages, cfg, cache: SummaryCache | None = None,
                      provider: SummaryProvider | None = None) -> DemoDigest:
    result = build_ranked_digest(context, messages, cfg)
    assert len(result.digest) <= 5
    authorized = set(result.eligible_ids)
    for ranked in result.digest:
        if not set(ranked.story.source_message_ids) <= authorized:
            raise ValueError('Downstream summary source escaped authorization')
    return DemoDigest(result, tuple(DemoItem(ranked, summarize_story(ranked.story, cache, provider))
                                    for ranked in result.digest))


def record_feedback(events, item: RankedStory, persona_id: str, as_of, relevant: bool, event_id: str):
    event = FeedbackEvent(event_id, persona_id, item.story.representative.topics, relevant, as_of)
    return apply_feedback(events, event)


def top3_jaccard(left: DigestResult, right: DigestResult) -> float:
    a = {x.story.story_id for x in left.digest[:3]}
    b = {x.story.story_id for x in right.digest[:3]}
    return len(a & b) / len(a | b) if a | b else 1.
