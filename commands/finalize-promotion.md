---
description: Close out a merged promote PR — flip leaves to decided, archive thread
---

Run the `finalize-promotion` skill. Verifies the PR merged via `gh`, flips each landed leaf from `in-review` to `decided` on main, appends `promoted_to` + `promoted_at`, and either returns the thread to `active/refining` for further work or archives it to `archive/`.
