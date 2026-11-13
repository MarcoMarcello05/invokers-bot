# Invokers Bot

Aktueller Arbeitsstand: **Arena Integration Sprint 01**. Vorhandene Reader,
Handoff-Priorität, V4-Navigation und Verifikation sind zu einem begrenzten
Autopiloten verbunden. Keine neue GUI und keine automatische Live-Freigabe.

```sh
python src/arena_runner.py --simulate --cycles 2
```

Windows-Vorbereitung und nächster sicherer PC-Test:
[docs/ARENA_SPRINT_01.md](docs/ARENA_SPRINT_01.md).

```sh
python -m unittest discover -s tests -v
```

Siehe [MASTER_STATUS.md](research/MASTER_STATUS.md) für belegte Fähigkeiten und
offene Windows-Gates. Ein erfolgreicher Simulationstest belegt keinen Live-Erfolg.
Private Konfigurationen, neue Spielaufnahmen und Laufzeitberichte gehören nicht
in Git. Das bereits vorhandene allgemeine GameState/Planner-Fundament wird
beibehalten; dieser Sprint erweitert ausschließlich den Arena-Ausführungspfad.
