# PROJECT WORKFLOW

Date: 2026-11-14

This file defines the permanent working split for the Invokers Bot project.

## Roles

### ANALYSER chat
The ANALYSER owns:
- planning,
- architecture,
- research,
- game-system inventory,
- data analysis,
- technical decisions,
- prioritization,
- acceptance criteria,
- review of developer results,
- GitHub documentation.

The ANALYSER **does not implement production bot code** when implementation work is needed. Instead it writes a concrete developer prompt.

### DEVELOPER chat
The DEVELOPER owns:
- coding,
- tests,
- fixes,
- implementation,
- commits,
- pushes,
- proof that remote GitHub contains the finished work.

Every coding task should arrive as a structured prompt containing:
1. goal,
2. context,
3. exact files/inputs,
4. researched findings/sources,
5. chosen design,
6. implementation requirements,
7. tests,
8. acceptance criteria,
9. risks,
10. commit/push requirements.

### USER
The USER supplies:
- fresh game files,
- screenshots,
- recordings,
- practical Windows-client tests,
- decisions when a real tradeoff needs user preference.

## Research rule

Before a new technical theme, parser strategy, architecture choice, automation method or major implementation decision:
- search the current web,
- inspect relevant GitHub projects/docs/issues when useful,
- prefer primary/official sources,
- record the relevant findings and links in the repository.

Do not rely on memory alone for current technical facts.

## Source-of-truth files

- MASTER_CHECKLIST.md = complete project target list
- MASTER_STATUS.md = current high-level state
- MASTER_PLAN.md = ordered development strategy
- GAME_KNOWLEDGE.md = researched game systems
- RESEARCH.md = external technical/game research
- ARCHITECTURE.md = accepted architecture
- DECISIONS.md = durable decisions
- DEVELOPER_HANDOFF.md = current developer-ready package
- TEST_RESULTS.md = verified results

## Working loop

ANALYSER:
research -> inspect data -> decide -> document -> create developer prompt

DEVELOPER:
implement -> test -> commit -> push -> report exact evidence

ANALYSER:
review -> verify remote -> update checklist/status -> plan next package

No major feature should skip this loop.
