# Demo script (about 2–3 minutes)

**0:00–0:20 — Problem.** “Hardware teams make decisions in Slack, but the important facts are spread across channels and threads. A mechanical engineer, a supply-chain lead, and an engineering manager should not receive the same digest.” Point to the fixed demo clock and 72-hour lookback.

**0:20–0:45 — Sarah Chen (ME), Prototype.** Show her Digest. The chassis service-panel fit risk and motor-mount vibration rise to the top. Each card has a source channel, timestamp, and original message; there are at most five stories.

**0:45–1:05 — Why Ranked.** Expand S-M019. Show the six raw scores and weighted contributions. Explain that her chassis ownership and current integration priority matter, and the Severity Floor protects this risk. Ranking, not the LLM, selected the story.

**1:05–1:30 — Compare.** Open Compare for Sarah Chen (ME), Raj Patel (SC), and Marcus Lee (EM). The same snapshot yields mechanical fit, supplier lead time, and milestone/dependency priorities. Point to their Top-3 IDs and overlap. Marcus can see a private leadership schedule update; Sarah and Raj cannot.

**1:30–1:50 — Phase change.** Keep Raj Patel (SC) selected and switch Prototype to Production. S-M050 enters his Top-3; supplier inspection and release evidence become more important. No synthetic messages or ranking weights changed.

**1:50–2:15 — Differences and trust.** Return to Sarah’s vibration story: M001/M002 report different measurements under the same stated conditions, so the UI calls it a conflict and preserves both sources. Switch to Priya Nair (EE): M012/M013 and M009/M010 show *Unresolved difference* because conditions or versions are not directly comparable. The summary never decides which source is correct.

**2:15–2:35 — Feedback and fallback.** Click Relevant or Not Relevant; the next ranking changes slightly, while ACL and the Severity Floor still apply. The demo works without an API key through deterministic, source-grounded summaries.

**2:35–2:50 — Close with architecture.** “ACL and retrieval narrow the evidence; grouping preserves differences; six-signal ranking and the Severity Floor decide what matters; only final Top-K stories reach the summarizer.” Show the architecture diagram.
