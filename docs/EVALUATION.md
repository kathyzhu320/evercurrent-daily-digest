# Formal evaluation — frozen human-reviewed labels

> All 20 baseline persona × phase relevance sets, five stress sets, and nine relationship-pair labels were human-reviewed and approved before the formal run. The ground truth is frozen by `eval/labels.sha256`; the evaluator checks that fingerprint before producing `eval/results.json`. Runtime ranking does not read these labels.

## Precision@5 — 20 baseline scenarios

Precision@5 counts relevant story IDs in the five selected slots, divided by five. Labels are independent of runtime ranking. The original per-scenario target is 0.60; failures are retained.

| Persona | Phase | P@5 | Relevant / 5 | Top-5 story IDs |
| --- | --- | ---: | ---: | --- |
| Sarah Chen (ME) | Design | 0.40 | 2/5 | S-M001, S-M019, S-M040, S-M024, S-M049 |
| Sarah Chen (ME) | Prototype | 1.00 | 5/5 | S-M019, S-M001, S-M049, S-M044, S-M040 |
| Sarah Chen (ME) | Validation | 0.80 | 4/5 | S-M001, S-M049, S-M044, S-M040, S-M019 |
| Sarah Chen (ME) | Production | 0.80 | 4/5 | S-M027, S-M025, S-M001, S-M019, S-M046 |
| Priya Nair (EE) | Design | 0.80 | 4/5 | S-M043, S-M012, S-M009, S-M054, S-M057 |
| Priya Nair (EE) | Prototype | 0.60 | 3/5 | S-M054, S-M012, S-M009, S-M055, S-M048 |
| Priya Nair (EE) | Validation | 0.80 | 4/5 | S-M009, S-M012, S-M054, S-M043, S-M055 |
| Priya Nair (EE) | Production | 0.80 | 4/5 | S-M029, S-M012, S-M009, S-M043, S-M054 |
| Raj Patel (SC) | Design | 0.40 | 2/5 | S-M056, S-M005, S-M046, S-M051, S-M012 |
| Raj Patel (SC) | Prototype | 0.80 | 4/5 | S-M005, S-M046, S-M033, S-M056, S-M012 |
| Raj Patel (SC) | Validation | 0.60 | 3/5 | S-M005, S-M050, S-M030, S-M026, S-M009 |
| Raj Patel (SC) | Production | 0.60 | 3/5 | S-M005, S-M033, S-M050, S-M046, S-M012 |
| Marcus Lee (EM) | Design | 0.40 | 2/5 | S-M014, S-M042, S-M032, S-M017, S-M053 |
| Marcus Lee (EM) | Prototype | 0.60 | 3/5 | S-M014, S-M037, S-M017, S-M032, S-M005 |
| Marcus Lee (EM) | Validation | 0.60 | 3/5 | S-M014, S-M037, S-M032, S-M052, S-M005 |
| Marcus Lee (EM) | Production | 0.80 | 4/5 | S-M014, S-M032, S-M037, S-M052, S-M053 |
| Lena Torres (PM) | Design | 0.60 | 3/5 | S-M023, S-M053, S-M014, S-M042, S-M032 |
| Lena Torres (PM) | Prototype | 0.40 | 2/5 | S-M014, S-M038, S-M017, S-M032, S-M053 |
| Lena Torres (PM) | Validation | 0.40 | 2/5 | S-M014, S-M038, S-M032, S-M053, S-M045 |
| Lena Torres (PM) | Production | 0.80 | 4/5 | S-M053, S-M014, S-M032, S-M031, S-M045 |

**Macro mean 0.65; minimum 0.40; maximum 1.00.** Fifteen of twenty scenarios meet 0.60; five do not.

### Five approved stress scenarios

These targeted cases exercise priority narrowing, expiration, and feedback behavior; their labels were reviewed independently of the output.

| Scenario | P@5 | Top-5 story IDs |
| --- | ---: | --- |
| Sarah / vibration priority | 1.00 | S-M001, S-M040, S-M019, S-M049, S-M044 |
| Sarah / thermal priority | 0.60 | S-M055, S-M036, S-M009, S-M019, S-M001 |
| Raj / narrow priority and negative feedback | 0.40 | S-M001, S-M040, S-M005, S-M046, S-M012 |
| Sarah / expired priorities | 1.00 | S-M019, S-M001, S-M049, S-M044, S-M040 |
| Priya / decayed feedback | 0.60 | S-M054, S-M009, S-M012, S-M055, S-M048 |

Raj's narrow vibration priority pulls unrelated mechanical stories into the Top-5, while the sourcing risk S-M005 remains through the Severity Floor. This stress result is reported as a limitation; the labels and frozen ranking were not changed to improve it.

### Why five scenarios miss

- **Sarah Chen (ME), Design — 0.40:** vibration remains a real mechanical risk, but recent prototype calibration and integration-testing updates rank above several design-stage CAD/service-access facts in the approved Design relevance set. Phase is a score, not a hard content filter.
- **Raj Patel (SC), Design — 0.40:** current lead-time and delivery signals remain strong under supplier priorities; production-oriented receiving and a battery-interface risk also enter the Top-5, while Design labels favor BOM and second-source decisions.
- **Marcus Lee (EM), Design — 0.40:** milestone and dependency visibility brings a public checkpoint, later quality acceptance, and a private commercial risk into the Top-5. The Design labels emphasize architecture/scope and early cross-team choices.
- **Lena Torres (PM), Prototype — 0.40:** milestone and commercial urgency raises schedule, acceptance, and late-delivery exposure. The Prototype labels favor pilot scope, demo script, and immediate build implications.
- **Lena Torres (PM), Validation — 0.40:** a mix of private commercial risk, acceptance, and prototype demo content outranks some validation-specific safety/reliability evidence. No weights, data, or labels were changed to hide this miss.

## Persona divergence — Prototype Top-3

| Pair | Jaccard |
| --- | ---: |
| Sarah Chen (ME) / Priya Nair (EE) | 0.00 |
| Sarah Chen (ME) / Raj Patel (SC) | 0.00 |
| Sarah Chen (ME) / Marcus Lee (EM) | 0.00 |
| Sarah Chen (ME) / Lena Torres (PM) | 0.00 |
| Priya Nair (EE) / Raj Patel (SC) | 0.00 |
| Priya Nair (EE) / Marcus Lee (EM) | 0.00 |
| Priya Nair (EE) / Lena Torres (PM) | 0.00 |
| Raj Patel (SC) / Marcus Lee (EM) | 0.00 |
| Raj Patel (SC) / Lena Torres (PM) | 0.00 |
| Marcus Lee (EM) / Lena Torres (PM) | 0.50 |

Nine of ten pairwise values are below 0.50. Marcus Lee (EM) / Lena Torres (PM) is 0.50: milestone and dependency visibility is intentionally shared, so overlap is business-reasonable.

## Phase sensitivity — Prototype → Production

| Persona | Prototype Top-3 | Production Top-3 | Entered |
| --- | --- | --- | --- |
| Sarah Chen (ME) | S-M019, S-M001, S-M049 | S-M027, S-M025, S-M001 | S-M025, S-M027 |
| Priya Nair (EE) | S-M054, S-M012, S-M009 | S-M029, S-M012, S-M009 | S-M029 |
| Raj Patel (SC) | S-M005, S-M046, S-M033 | S-M005, S-M033, S-M050 | S-M050 |
| Marcus Lee (EM) | S-M014, S-M037, S-M017 | S-M014, S-M032, S-M037 | S-M032 |
| Lena Torres (PM) | S-M014, S-M038, S-M017 | S-M053, S-M014, S-M032 | S-M032, S-M053 |

All five personas change at least one Top-3 story with persona and priorities held fixed.

## Relationship checks — nine approved pair labels

| Intended class | Matched / labeled |
| --- | ---: |
| Duplicate | 3/3 |
| Superseded | 2/2 |
| Conflict | 1/1 |
| Unresolved Difference | 3/3 |

Zero of three different/unverified-condition pairs were presented as comparable scientific conflicts. The evaluation maps the unchanged internal `CONFLICT` relationship with `comparable=false` to the reviewer-facing `Unresolved difference` class. This is a nine-pair labeled check, not an estimate of corpus-wide precision or recall.

## Summary faithfulness

Across 25 baseline/stress runs, all **125/125** final no-key summaries passed the identifier-level source check (**100%**). A simulated provider answer containing unsupported `999V` was rejected and replaced with the deterministic source-backed summary. This checks **identifier-level factual consistency, not full semantic hallucination detection**. No live OpenAI credential was used.

## Reproduce

Run `python eval/evaluate.py` from the repository root to reproduce the formal results in `eval/results.json`. The script refuses labels that are unapproved, unfrozen, or different from `eval/labels.sha256`.
