from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timedelta
from typing import Any


def utc(value: str | datetime) -> datetime:
    result = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError('Explicit UTC timestamp required')
    return result


def primitive(value: Any) -> Any:
    if is_dataclass(value):
        return {f.name: primitive(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, datetime):
        return value.isoformat().replace('+00:00', 'Z')
    if isinstance(value, dict):
        return {k: primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [primitive(v) for v in value]
    return value


@dataclass(frozen=True)
class Identifier:
    kind: str
    value: str
    unit: str
    raw: str
    start: int
    end: int
    source_message_id: str

    @property
    def key(self):
        return self.kind, self.value, self.unit


@dataclass(frozen=True)
class Message:
    message_id: str
    channel: str
    timestamp: datetime
    author: str
    author_role: str
    thread_id: str
    text: str
    project: str = 'Atlas'
    phase: str = 'Prototype'
    parent_id: str | None = None
    reactions: int = 0
    topics: tuple[str, ...] = ()
    message_type: str = 'fyi'
    severity: float = .2
    affects: tuple[str, ...] = ()
    entities: tuple[Identifier, ...] = ()
    reply_count: int = 0
    entity: str = ''
    metric: str = ''


@dataclass(frozen=True)
class Persona:
    persona_id: str
    name: str
    role: str
    owns: tuple[str, ...]
    channels: tuple[str, ...]
    default_priorities: tuple[str, ...]


@dataclass(frozen=True)
class Priority:
    topic: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class FeedbackEvent:
    event_id: str
    persona_id: str
    topics: tuple[str, ...]
    relevant: bool
    timestamp: datetime


@dataclass(frozen=True)
class UserContext:
    persona: Persona
    phase: str
    priorities: tuple[Priority, ...]
    as_of: datetime
    feedback: tuple[FeedbackEvent, ...] = ()
    project: str = 'Atlas'
    exact_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class Relationship:
    label: str
    source_ids: tuple[str, str]
    evidence: str
    differences: dict
    comparable: bool = False


@dataclass(frozen=True)
class Story:
    story_id: str
    messages: tuple[Message, ...]
    representative: Message
    label: str
    relationships: tuple[Relationship, ...]
    identifier_differences: dict
    context_messages: tuple[Message, ...] = ()

    @property
    def source_message_ids(self):
        return tuple(sorted({m.message_id for m in self.messages + self.context_messages}))


@dataclass(frozen=True)
class ScoreBreakdown:
    raw: dict[str, float]
    weighted: dict[str, float]
    final_score: float
    matched_priorities: tuple[str, ...]
    owns_affects: tuple[str, ...]
    role_topics: tuple[str, ...]
    phase_topics: tuple[str, ...]
    floor_eligible: bool


@dataclass(frozen=True)
class RankedStory:
    story: Story
    score: ScoreBreakdown
    category: str
    protected: bool = False


@dataclass(frozen=True)
class DigestResult:
    as_of: datetime
    eligible_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    retrieval_reasons: dict[str, tuple[str, ...]]
    ranked: tuple[RankedStory, ...]
    digest: tuple[RankedStory, ...]
