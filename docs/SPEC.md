# EverCurrent Adaptive Daily Digest — Product and Technical Specification

This reviewer-facing specification describes the implemented interview MVP. The [README](../README.md) is the fastest entry point; this document preserves the exact ranking hypotheses and core behavior for technical review.

## Product contract

Project Atlas is a synthetic Slack-style snapshot for mechanical engineering, electrical engineering, supply chain, engineering management, and product management. The digest uses a fixed UTC clock (`2026-09-27T18:00:00Z`) and a 72-hour inclusive lookback. Role, current project phase, explicit priorities, and decayed feedback change selection. One digest contains at most five authorized stories. The role is fixed by the chosen persona; the project is Atlas. This is an interview MVP, not a production Slack integration.

**Ranking decides what matters. The optional LLM only summarizes final selected evidence.** No model controls ACL, candidate eligibility, grouping, conflict classification, or relevance.

## Flow and access

ACL plus project/time metadata are applied before candidate retrieval. TF-IDF cosine similarity and keyword/priority/exact-identifier union generate candidates. Story grouping keeps duplicates, explicit update chains, and unresolved critical differences with all authorized source IDs. The fixed six-signal formula ranks stories. Severity Floor protects at most two eligible blocker/risk stories from the full authorized pool (Role ≥ 0.3), replacing lower unprotected slots inside K ≤ 5. The summarizer then sees only final authorized stories; source identifiers in the resulting text are checked and unsafe output falls back deterministically.

## Scoring and personalization

`Final Score = 0.25 Role + 0.25 Priority + 0.20 Phase + 0.15 Severity + 0.10 Recency + 0.05 Feedback`.

Role and Phase are read from the matrices below, with ownership and severity attention rules implemented in the core. Explicit priority primary-topic match is 1.0, secondary-topic match 0.6, otherwise 0; priorities expire after seven days. Recency has a 48-hour half-life. A Relevant / Not Relevant event changes topic preference by ±0.2, clipped to [-1, 1], with a seven-day half-life; no history scores 0.5. Scores and weighted contributions are shown in Why Ranked. Weights are configurable MVP hypotheses, not trained optima.

## Engineering relationships

Critical identifiers retain type, value, unit, raw span, and source: measurements, voltage/current, RPM, lead time, revisions, part IDs, dates, error codes, temperature, and percentages. A duplicate repeats the same factual update. Supersession requires the same entity/metric and an explicit update or replacement relationship; sharing a thread or author is insufficient. M001/M002 are same-condition measurements with different values and may be shown as Conflict. M001/M003, M009/M010, and M012/M013 have different or insufficiently comparable conditions and are shown as Unresolved difference. Underlying relationship evidence remains visible. No LLM chooses the correct source.

## Evaluation and limitations

Human-reviewed labels are stored outside runtime in `eval/labels.json`. The offline evaluation reports 20 baseline Precision@5 results, Prototype persona overlap, Prototype-to-Production changes, labeled relationship pairs, and identifier-level summary checking. See [EVALUATION.md](EVALUATION.md). The synthetic dataset, rule-based enrichment, TF-IDF backend, no-key deterministic fallback, session-only feedback, and absence of real Slack OAuth/events are deliberate MVP limits. Identifier-level checking is not full semantic faithfulness.

## Exact matrices

The approved matrices below are configuration hypotheses, not learned parameters. They match `config/topics.yaml` exactly.

### 7.3 Role × Topic

| Topic | ME | EE | SC | EM | PM |
| --- | --- | --- | --- | --- | --- |
| vibration | 1.0 | 0.4 | 0.1 | 0.6 | 0.3 |
| motor | 0.8 | 0.8 | 0.4 | 0.5 | 0.3 |
| integration | 1.0 | 0.6 | 0.1 | 0.6 | 0.3 |
| tolerance | 1.0 | 0.2 | 0.5 | 0.3 | 0.1 |
| testing | 0.8 | 0.8 | 0.2 | 0.7 | 0.5 |
| thermal | 0.6 | 1.0 | 0.1 | 0.6 | 0.4 |
| battery | 0.4 | 1.0 | 0.5 | 0.5 | 0.4 |
| firmware_if | 0.2 | 1.0 | 0.0 | 0.4 | 0.2 |
| supplier | 0.3 | 0.4 | 1.0 | 0.5 | 0.4 |
| lead_time | 0.3 | 0.5 | 1.0 | 0.7 | 0.7 |
| quality | 0.5 | 0.5 | 0.8 | 0.7 | 0.5 |
| milestone | 0.4 | 0.4 | 0.5 | 1.0 | 1.0 |
| dependency | 0.5 | 0.5 | 0.5 | 1.0 | 0.7 |
| scope | 0.2 | 0.2 | 0.2 | 0.6 | 1.0 |
| design_decision | 0.8 | 0.8 | 0.3 | 0.6 | 0.6 |

### 7.4 Phase × Topic

| Topic | Design | Prototype | Validation | Production |
| --- | --- | --- | --- | --- |
| vibration | 0.3 | 0.9 | 0.8 | 0.4 |
| motor | 0.6 | 0.8 | 0.7 | 0.5 |
| integration | 0.5 | 1.0 | 0.7 | 0.4 |
| tolerance | 0.8 | 0.6 | 0.5 | 0.9 |
| testing | 0.2 | 1.0 | 1.0 | 0.4 |
| thermal | 0.5 | 0.8 | 1.0 | 0.5 |
| battery | 0.5 | 0.8 | 0.9 | 0.5 |
| firmware_if | 0.6 | 0.8 | 0.8 | 0.3 |
| supplier | 0.3 | 0.5 | 0.5 | 1.0 |
| lead_time | 0.3 | 0.5 | 0.6 | 1.0 |
| quality | 0.1 | 0.4 | 0.8 | 1.0 |
| milestone | 0.4 | 0.7 | 0.8 | 0.9 |
| dependency | 0.5 | 0.8 | 0.7 | 0.8 |
| scope | 0.8 | 0.5 | 0.3 | 0.2 |
| design_decision | 1.0 | 0.6 | 0.3 | 0.2 |

