---
name: research
description: Use when a task requires investigation, source selection, fact checking, current information, comparison of alternatives, or an evidence-backed summary.
---

# Research

Use this workflow for investigation tasks where the answer should be grounded in sources, reproducible reasoning, or explicit uncertainty.

## Track Note Workflow

When the user asks for research, create a track note for the investigation before doing substantial work.

1. Choose a concise note title that names the research topic and prefix it with the current date as `yyyyMMdd`.
2. Create the note with the `research` tag:

```sh
track new --title "yyyyMMdd <topic> research" --tag research
```

3. Record the research in the note using this simple structure:

```md
## Question

## Summary

## Findings

## Sources

## Open Questions
```

4. Keep source URLs, local file paths, commands, and dates in the note while investigating.
5. Update the note with the final summary and any unresolved questions before giving the user the final answer.
6. In the final answer, mention the track note title or path when available.

If the track CLI is unavailable or note creation fails, continue the research and tell the user that the note could not be created.

## Triage

1. Restate the research question in one sentence when it helps narrow scope.
2. Identify whether the answer depends on current facts, primary sources, product documentation, law, pricing, schedules, or other unstable information.
3. If current or high-stakes accuracy matters, gather fresh sources before answering.
4. Prefer primary sources: official documentation, standards, papers, source repositories, government pages, release notes, or first-party announcements.
5. Use secondary sources only to discover leads, compare interpretations, or fill context that primary sources do not provide.

## Source Handling

- Track which source supports each material claim.
- Prefer fewer strong sources over many weak ones.
- Check publication dates and event dates separately.
- Treat marketing copy, generated summaries, and unsourced blog posts as weak evidence.
- If sources disagree, report the disagreement instead of flattening it.
- If a claim is an inference, label it as an inference.

## Investigation Loop

1. Search broadly enough to find the right source class.
2. Narrow to primary or authoritative references.
3. Read the relevant sections directly.
4. Extract the facts needed for the user's decision.
5. Note open questions, stale data risk, and assumptions.
6. Stop once the answer is sufficiently supported for the user's requested depth.

## Output

Keep the final answer compact and useful:

- Lead with the answer or recommendation.
- Include the minimum source context needed to verify it.
- Separate facts, interpretation, and uncertainty.
- Use dates for time-sensitive claims.
- Provide links or local file references when available.
- Avoid dumping raw notes unless the user asks for them.

## When Working In A Repository

- Read local docs and existing conventions before proposing changes.
- Prefer local project sources over external assumptions.
- If creating follow-up implementation guidance, include exact files and commands.
- Keep research artifacts close to the plugin or project area they support.
