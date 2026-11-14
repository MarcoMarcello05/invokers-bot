# CLAN MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerClanModel.dat

Raw account files are not committed.

## PlayerClanModel

Current payload:
- VersionTolerant member count: 19
- current IL2CPP field count: 19
- no reserved gaps observed

Verified slot order follows the current field set:

0 Membership
1 PendingJoinRequestClanIds
2 JoinRequestsSentToday
3 PendingInviteClanIds
4 InvitesSentToday
5 LeaveOrKickCount
6 DailyActivity
7 PendingActivityChest
8 DailyBossActivity
9 PendingBossChest
10 NextPenaltyFreeClanChangeAtUtc
11 LastClaimedActivityChestDayUtc
12 LastClaimedBossChestDayUtc
13 DailyActivityToActualize
14 DailyBossActivityToActualize
15 LastLeftClanAtUtc
16 LastKickedClanId
17 LastKickedRewardsProcessedDayUtc
18 Boss2

Current slot 18 contains a PlayerClanBoss2State object with 5 members.

## PlayerClanBoss2State

Current schema:
0 DayUtc
1 ReplaysUsed
2 StartedDifficulties
3 Chests
4 BestDamageByDifficulty

The supplied snapshot's Boss2 object has exact member lengths:
8, 4, 4, 4, 4.

## PlayerClanBoss2Chest

Fields:
- ClanId
- DayUtc
- DifficultyId
- Damage
- Tier
- BossDefeated
- PersonalClaimed
- KillClaimed
- Forfeited

Derived properties:
- Claimed
- HasPendingReward

## Bot value

Clan logic can use structured state for:
- whether player is in a clan
- daily activity state
- pending activity/boss chest state
- clan change penalty window
- Clan Boss 2 replay usage
- started difficulties
- best damage by difficulty
- claim eligibility

Vision should navigate/verify the clan UI rather than infer these facts via OCR.
