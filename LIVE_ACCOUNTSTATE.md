# Live AccountState integration

Optional startup: `python -m invokers_bot.app --mode live --snapshot-dir "C:\\path\\aggregate_snapshots"`.
Alternatively set runtime.snapshot_dir in local config. Select the active account directory explicitly; no automatic account selection.

BotEngine._observe updates screen/confidence and polls AccountObserver every 0.5 seconds. An unchanged file stamp avoids parsing. Actual input invalidates all currently known aggregate observations conservatively and forces a read immediately and after visual transition. Unchanged content remains awaiting_change until changed bytes appear; this is not proof a particular action succeeded. Missing/corrupt/concurrently changed files retain last good state for diagnostics but get_fresh refuses it. Source versions and timestamps are carried by parsed models. Independent aggregates are not atomic; joins need consistency/freshness checks. Existing configured CV flows still execute through SendInput; scheduler goals have not yet been rewired to AccountState. No snapshot writes. No event watcher needed for this first integration; metadata polling catches delayed saves. A later watcher can be a wake-up hint rather than a correctness dependency.

Next: connect normalized fresh facts to goal eligibility, define action-specific invalidation and verification predicates, validate real client save latency and account selection. Existing templates and actual Windows input need real client validation.
