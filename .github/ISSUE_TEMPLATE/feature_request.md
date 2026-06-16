---
name: Feature Request
about: Suggest a feature
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

## Problem

Describe the problem this feature would solve. What's missing or difficult?

Example: "It's hard to know which notes are outdated because I have no way to see which ones were modified recently."

## Solution

Describe the solution you'd like. How would it work?

Example: "Add a 'Last Modified' column to the search results so I can see which notes are recent."

## Why

Why is this important? What would it enable?

Example: "This would help me keep my vault organized and identify stale notes for cleanup."

## Alternatives

Any other approaches you've considered?

Example: "Could use a separate 'recent notes' view, but per-result timestamps would be more useful."

## Example Usage

Show how someone would use this feature:

```bash
curl http://localhost:8765/query \
  -d '{"text": "Recent project notes", "filter": "modified:1w"}'
```

## Additional Context

- Is this feature related to a specific query mode?
- Would this require config changes?
- Any relevant existing features?

## Implementation Notes

If you have ideas about implementation:
- **Where** would this live? (new endpoint? config option? UI change?)
- **What** would need to change? (database schema? LLM prompt? API?)
- **How** complex would it be? (small / medium / large)
