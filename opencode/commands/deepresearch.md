---
description: Run the deep-research loop on a topic (hot brainstorm subagent, default-temperature gating)
---

Run the deep-research protocol (Research\deep_research_agent_design.md, section 4) on the topic: $ARGUMENTS

Temperature is intrinsic to this command — never ask the user to switch models or variants:

1. **Frame.** Restate the research question in 1–2 sentences. Decompose into 3–6 first-round sub-questions covering: definition/basics, established measurements, practical conditions, known disagreements. If the topic already has a report (`Research\deep-research\<topic>\report.md`), open it in the Review pane with the browser `preview` tool right away, so the user sees the current state before the new rounds start.
2. **Research rounds.** One `deepresearch_deep_research` (or `deep_research`) call per sub-question (topic = lowercase hyphenated slug, e.g. `raising-neocaridina-shrimp`). The homelab server handles DuckDuckGo/Bing SERP and real-browser TLS impersonation automatically. If you find specific URLs by other means (your own search, citations, DOI pages), add them with `deepresearch_fetch_url` (or `fetch_url`) (url, topic, title).
3. **Evaluate.** Per source: what does it claim, what method/evidence, who wrote it (tier tag), how current. Tag each useful claim with its source id. Use `cite` (or `deepresearch_cite`) to read specific source excerpts.
4. **Brainstorm (HOT).** Spawn the `brainstorm` subagent — it runs on the `#hot` temperature variant internally; this is the only hot-temperature step and the session's own model is never changed, so there is nothing to revert. Pass it the question, current findings, and open questions, and ask for 3x candidates across the families. If the brainstorm subagent is unavailable (variant not configured), do the over-generation inline at the current temperature instead.
5. **Gate (default temperature).** Filter the candidate list through the gates: relevance (would the answer change the report?), novelty (not answered by cached sources — check `deepresearch_list_sources` + notes first), dedup (not a rephrase of an open question in notes.md). Survivors become the next round's questions.
6. **Journal.** Use `deepresearch_save_note` (or `save_note`) to record every material finding, open question, and contradiction as it happens.
7. **Converge.** Stop when: all open questions are answered or judged unanswerable, a round produced no new findings, or the ~10-round cap is hit.
8. **Synthesize & Save (Local File + Homelab Archive).**
   Synthesize the complete, comprehensive research report containing: summary answer, findings by sub-question, **investigation map**, contradictions section (both sides, never silent picks), source list (id → url, tier, date), open questions, and confidence assessment. Every non-obvious claim carries an `[s#]` citation.
   The **investigation map** contains two mermaid blocks placed right after the title/metadata, before the summary answer:
   - a `timeline` — one entry per research round: what was asked, key sources with s# ids, the outcome. Include wrong-organism and dead-end rounds; the map must show the whole path, not just the successes.
   - a `mindmap` — topic → sub-questions → key findings tagged with s# ids, with open questions as their own branch.
   Keep each diagram under ~20 nodes; no colons or parentheses inside mermaid node text.

   **CRITICAL DUAL-SAVE & LOCAL PREVIEW STEPS:**
   a. **Save Locally:** You MUST write the full markdown report directly to the local workspace file:
      `Research/deep-research/<topic>/report.md`
      using your local file writing tool (`write_file`). Create parent directories if needed. The user must have the physical markdown file on their local machine.
   b. **Archive to Cluster:** Also call `deepresearch_save_report` (or `save_report`) to archive the report on the homelab cluster.
   c. **Open in Preview:** Open the local file `Research/deep-research/<topic>/report.md` in the Review/preview pane with `browser.preview` (pass the local path). (You can also provide the LAN URL `http://192.168.1.67:8001/reports/<topic>` for browser viewing).

When finished, report: the answer summary, the local file path (`Research/deep-research/<topic>/report.md`), the LAN URL (`http://192.168.1.67:8001/reports/<topic>`), and anything that fell short or needs follow-up.
