# Invokers Live Bot

Clean-room Windows live-bot foundation for **Invokers: Titan Legacy**.

## What it does

- Finds the Invokers window and client area.
- Reads DPI and uses client-relative geometry.
- Captures the game with DXcam, with MSS fallback.
- Detects known states via OpenCV template matching.
- Requires stable recognition across frames.
- Executes real Windows mouse/keyboard input in `live` mode.
- Re-observes after actions.
- Saves diagnostic screenshots for persistent UNKNOWN states.
- Never clicks while the state is UNKNOWN.
- F12 stops the bot globally.

## Install

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -U pip
pip install -e .
```

## Dry run

```bat
python -m invokers_bot.app --config config/arena.json --mode dry
```

## LIVE

```bat
python -m invokers_bot.app --config config/arena.json --mode live
```

The clean rebuild deliberately contains no guessed coordinates and no copied legacy templates. Fresh current-game screenshots/templates are the final requirement before a practical autonomous Arena run can be validated.
