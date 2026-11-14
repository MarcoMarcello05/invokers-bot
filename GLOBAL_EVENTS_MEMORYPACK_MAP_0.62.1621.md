# GLOBAL EVENTS MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerGlobalEventsModel.dat

Raw account files are not committed.

## PlayerGlobalEventsModel

Current payload is VersionTolerant with 3 members:

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | TournamentsById | 1862 |
| 1 | FinishedNoviceTournament | 1 |
| 2 | CompletedNoviceTournamentGroupIds | 4 |

Current TournamentsById dictionary count = 9.

## TournamentParticipationState

The current IL2CPP model is a MemoryPack union/abstract participation state family.

Known common fields include tournament identity and joined-at state, with derived participation variants exposing scoring/reward state.

Because the current snapshot contains nine tournament entries, this model is a strong future source for:
- active tournament participation
- tournament progress
- unlocked/claimed reward state
- scoring context

Exact derived-union tag mapping should be documented before implementing nested tournament parsing.

## Development sequencing

Top-level PlayerGlobalEventsModel parsing is straightforward.
Nested TournamentParticipationState parsing should be a separate package after union tags and all derived layouts are mapped.
