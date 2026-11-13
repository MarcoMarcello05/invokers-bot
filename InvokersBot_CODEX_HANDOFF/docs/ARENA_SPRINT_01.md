# Arena-Autopilot – Integration Sprint 01

Der vorhandene Python-Bot startet über `src/arena_runner.py`, ohne neue GUI.
Standard ist eine Aufnahme/Planung **ohne Eingaben**. Navigation ist ein eigener
Dry-Run-Schritt. Kämpfe erfordern explizite Aktivierung **und** einen frischen,
passenden Navigations-Preflight. Simulation ist kein Windows-/Live-Nachweis.

## Integration und Grenzen

- `arena_actor.py`: Handoff-Priorität und begrenzte Top-/Down-Scrollsuche wiederverwendet;
  nur der geplante Gegner wird gesucht. Keine Teilstring-/Präfixersatzidentität.
- `arena_snapshot.py`: kohärenter, altersgeprüfter Arena-/Ressourcen-Snapshot;
  aktuelle Gegner ausschließlich Feld 12. Nach Aktion neue Leseoperationen.
- `autonomy_bridge.plan_arena`: schwächster geeigneter strukturierter Gegner unter
  der manuell konfigurierten eigenen Kampfkraft, stabile Fehler-/Gegneridentität.
- `arena_autopilot.py`: OBSERVE → PLAN → ACT → VERIFY → RECOVER → REPLAN;
  maximal zehn Durchläufe, standardmäßig einer. Keine unendlichen Retry-Schleifen.
- `arena_windows.py`: vorhandene `screen_actor_v8`-OCR/Template-Helfer, genaue
  Bedienlabels/ROIs, eindeutige Zeilenbuttons, stabile Koordinaten, Vordergrund-
  und Geometrieprüfung. Keine OCR-Auswahl anhand gegnerischer Stärke.
- `state_reader`, `Safety`, `Verification`, `FailureMemory`: bestehende Ressourcen-
  und Ergebnisprüfung. Sieg/Niederlage benötigt UI **und** genau einen strukturierten
  offensiven Kampfzähler-Zuwachs sowie passenden Tokenverbrauch; Gem-Verlust stoppt.
- V4s Auswahl eines bloß sichtbaren stärkeren Gegners und AUTO-Einschalten wurden
  nicht übernommen. AUTO wird niemals aktiviert. In Kampfansichten muss AUS erkennbar sein.

Nur exakt ein Arena-Token ist als Kampfkostenvertrag vorgesehen. Vor dem Start
müssen Token-Symbol und die Zahl 1 im Startbutton bestätigt sein. Das Token-
Referenzsymbol ist fest und hashgeprüft; Konfiguration kann es nicht durch Gems
ersetzen. Die manuelle eigene Stärke ist autoritativ; der Formationswert muss
sie bestätigen und darf sie nicht durch OCR erhöhen.

Automatische bezahlte Refreshs sind gesperrt. Optional `--free-refreshes 1..3`
verlangt einen eindeutig als KOSTENLOS/FREE erkannten Refresh, unveränderte
Ressourcen und eine tatsächlich geänderte aktuelle Gegnerliste. Default ist 0;
Dry-Run führt auch mit Navigation **keinen** Refresh/Kampf aus. Fehlt die kostenlose
Beschriftung, stoppt der Bot. Er rät nicht anhand eines unbeschrifteten Buttons.

Nicht getestet: echte Windows-Eingaben, aktueller Spielclient, Battle-/Ergebnis-
Übergänge auf dem PC, native globale F8-Erkennung. Keine erfolgreiche Live-Session
wird behauptet. Alte Refenzbilder belegen nur Offline-OCR-/Template-Verhalten.
Die vorhandene allgemeine DRY-RUN-Architektur bleibt erhalten; andere Live-Module
werden durch den Arena-Schalter nicht freigegeben. Kein neuer EXE-/GUI-Sprint.

## Bewährte Open-Source-Ansätze

Die Auswahl folgt [Playwrights Actionability-Prinzipien](https://github.com/microsoft/playwright/blob/main/docs/src/actionability.md):
eindeutiges sichtbares Ziel, Stabilität, aktivierbarer Zustand, begrenztes Warten,
Fehler statt blindem Weiterklicken. Das wird auf vorhandene Desktop-Helfer
angewandt; Playwright wird nicht als neue Abhängigkeit eingeführt. Dazu kommen
[PyAutoGUI-Fail-Safe](https://pyautogui.readthedocs.io/en/latest/index.html#fail-safes)
und Zustandsprüfung statt pauschaler Wartezeiten. Gemacht wird kein vermeintlicher
Browser-DOM-Sicherheitsnachweis für einen Spielbildschirm.

## Exakte Vorbereitung auf Windows

Im Ordner `InvokersBot_CODEX_HANDOFF`, PowerShell, offizielles Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-arena.txt
$py = '.\.venv\Scripts\python.exe'
$cfg = Join-Path $env:LOCALAPPDATA 'InvokersBot\user_config.json'
$cal = Join-Path $env:LOCALAPPDATA 'InvokersBot\arena_calibration.json'
$out = Join-Path $env:LOCALAPPDATA 'InvokersBot\arena_runs'
$game = Join-Path $env:USERPROFILE 'AppData\LocalLow\Hit_Zone\Invokers'
$power = [int](Read-Host 'Aktuelle eigene Arena-Kampfkraft')
```

Falls keine UserConfig existiert:

```powershell
& $py src\arena_runner.py --init-config --config $cfg --root $game --arena-power $power
```

Bestehende Dateien werden nicht überschrieben. Eine vorhandene UserConfig im
Texteditor prüfen (`game_root`, `arena_combat_power`, `modules.arena=true`).
Kampfkraft nach Teamänderungen selbst aktualisieren. Keine Geheimnisse eintragen.

Einmalig das überprüfbare Kalibrierungsbeispiel erstellen:

```powershell
& $py src\arena_runner.py --write-calibration $cal
```

Der Referenzbereich ist **1920×1080** bei unverändertem Fenster-/Desktoplayout.
Es gibt keine automatische blinde Skalierung. ROI-Koordinaten, Fenstertitel und
Token-Kostenposition im JSON mit dem tatsächlichen Bildschirm vergleichen.
`operator_confirmed_auto_off` bleibt false, solange AUTO nicht manuell als AUS
bestätigt ist. Die Token-Referenz selbst darf nicht ausgetauscht werden.

### 1. Simulation, ohne Spiel

```powershell
& $py src\arena_runner.py --simulate --cycles 2 --output-dir $out
```

Erwartet: `COMPLETED`, `completed_cycles=2`. Es werden erfundene Testdaten
verwendet, keine gespeicherten Spielstände verändert und keine Eingaben gesendet.

### 2. Sicherer erster PC-Test, ohne Eingaben

Spiel im Vordergrund, bestehende Arena-Liste sichtbar lassen. Snapshots müssen
aktuell sein (Standard höchstens 300 Sekunden); Öffnen der Formation allein
aktualisiert die Dateien möglicherweise nicht. Keine kostenpflichtigen Aktionen
zum Erzwingen frischer Daten ausführen.

```powershell
& $py src\arena_runner.py --dry-run --config $cfg --calibration $cal --output-dir $out
```

Erwartet: `DRY_RUN`, zehn oder tatsächlich aktuell vorhandene Feld-12-Gegner,
korrekt geplantes schwächstes geeignetes Ziel, **keine** Klicks/Scrolls.
Bei `STALE_SNAPSHOT`, `UNKNOWN_DIALOG`, Geometrie-/OCR-Fehlern zuerst den Bericht
prüfen. Nicht durch große Altersgrenzen oder niedrigere Erkennungsschwellen kaschieren.

### 3. Navigations-Dry-Run, weiterhin ohne Kampf/Refresh

Dieser Schritt ist ausdrücklich eingabewirksam: Er darf Arena öffnen, begrenzt
scrollen und die eindeutig zugeordnete Gegnerzeile zur Formation öffnen. Er darf
weder den kostenpflichtigen Startbutton noch Refresh drücken. Spiel fokussieren:

```powershell
& $py src\arena_runner.py --dry-run --navigate --config $cfg --calibration $cal --output-dir $out
```

Erwartet: `WOULD_START_BATTLE`, `preflight_passed=true`, richtige Gegneridentität,
eigene Stärke stimmt mit Konfiguration überein, Token-Symbol/Zahl 1 erkannt,
keine Ressourcenänderung. **Hier endet der nächste angeforderte PC-Test.**
Den lokalen `report.json` und ggf. `failure.png` prüfen; nicht automatisch zu Git hinzufügen.

### Später: ausdrücklich aktivierter einzelner Live-Test

Erst nach erfolgreichem PC-Dry-Run, überprüfter Kalibrierung und bewusster eigener
Aktivierung. AUTO zuvor manuell AUS bestätigen und im Kalibrierungs-JSON bestätigen;
nach jeder Kalibrierungsänderung den Navigations-Dry-Run erneut durchführen.
Der erfolgreiche Bericht ist höchstens fünf Minuten gültig und an Kalibrierung,
Spielpfad und eigene Stärke gebunden. Zur Arena-Liste zurückkehren, dann:

```powershell
$preflight = Read-Host 'Vollständiger Pfad zum passenden erfolgreichen report.json'
& $py src\arena_runner.py --live --activate-arena-live --preflight $preflight --config $cfg --calibration $cal --cycles 1 --output-dir $out
```

Ohne beide Aktivierungsbedingungen keine Live-Eingaben. Kein automatisches
Bestätigen von Dialogen, kein AUTO-Einschalten. Ist der Kampf-/Ergebnisbildschirm
nicht bestätigt, wird gestoppt und nicht erneut gestartet. Mehr Durchläufe erst
nach überprüftem Einzeltest. Live-Schutzprüfungen sind keine Garantie gegen eine
unbekannte Spielversion oder falsche lokale Kalibrierung.

## Stopp, Fehler und Recovery

- **F8** wird global in einem separaten Windows-Thread abgefragt. Ein gesetzter
  Stopp verhindert die nächste Eingabe auch während einer laufenden OCR-Auswertung.
- PyAutoGUI-Fail-Safe bleibt immer aktiv: Maus in eine Bildschirmecke.
- Zusätzlich Ctrl+C oder eine Datei `STOP` in `$out` anlegen. Eine vorhandene
  STOP-Datei wird nicht automatisch gelöscht.
- Unbekannte Dialoge werden nie bestätigt. Recovery ist höchstens eine bestätigte
  Zurück-Aktion aus einer bekannten Formation, danach Stopp statt neuer Kampfversuch.
- Jeder Lauf hat `events.jsonl`, `report.json`; reale Fehler versuchen zusätzlich
  `failure.png` zu speichern. Ist Screenshot-Erfassung selbst defekt, ist der Pfad
  null, nicht ein vorgetäuschtes Bild. Bei Simulation gibt es kein reales Screenshot.
- Eine `arena.lock` verhindert parallele physische Sitzungen. Nach einem Absturz
  nur nach Prozessprüfung eine verwaiste Sperre manuell entfernen.

## Tests und datensparsame Builds

```powershell
& $py -m unittest discover -s tests -v
& $py tests\check_arena_reference_ui.py
```

Der zweite Befehl nutzt vorhandene Repository-Referenzbilder und echte OCR, aber
keinen Bildschirm/keine Eingaben. Private neue Vergleichsarchive sind nicht im Git.
Ohne sie erzeugt die Testsuite Vergleichsdaten aus bereits versionierten Beispielen;
optional kann lokal `INVOKERS_PRIVATE_COMPARE` auf ein privates Archiv zeigen.

Nach Commit kann ein Quellbuild aus **HEAD** erzeugt werden:

```powershell
& $py tools\build_arena_source.py --output dist\InvokersBot_Arena_Sprint01_source.zip
```

Er enthält den Python-Startweg, Arena-Tests, generische Templates und den benötigten
Ressourcen-Enum. Keine Spieler-Snapshots, privaten Vergleichsarchive, UserConfigs,
Manifeste, Logs oder Fehlerbilder. Es ist ein Quellbuild, keine getestete Windows-EXE.
