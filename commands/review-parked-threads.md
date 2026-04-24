---
description: Audit parked threads — surface actionable, stale, and hygiene-warning ones
---

Run the `review-parked-threads` skill. Read-only periodic audit. Categorizes parked threads as: (a) actionable (unpark_trigger set and the condition may have fired), (b) stale (parked ≥N days), (c) hygiene warnings (no unpark_trigger). Use on a weekly/monthly cadence.
