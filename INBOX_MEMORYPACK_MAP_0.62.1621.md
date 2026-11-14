# INBOX MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerInboxModel.dat

Raw account files are not committed.

## PlayerInboxModel

Current payload is VersionTolerant with 2 slots:

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | LastInboxItemId | 8 |
| 1 | ItemsById | 4 |

Current ItemsById is an empty dictionary.

## InboxItem schema

Current IL2CPP fields:
- Id
- Type
- Reward
- IsRead
- AddedAtUtc
- TournamentInfo
- TowerLeaderboardInfo

The current snapshot has no inbox items, so exact InboxItem historical MemoryPack slot order is not live-byte verified yet.

## Bot value

Once a non-empty inbox snapshot is captured, structured state can tell the bot:
- whether inbox rewards exist
- read/unread state
- reward payload
- tournament/tower context

Until then, do not implement the nested InboxItem parser from declaration order alone.
