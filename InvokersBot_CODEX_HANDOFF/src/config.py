MAX_DEFEATS_SAME_TARGET=2
SCREEN_W=1920
SCREEN_H=1080
OCR_MIN_CONFIDENCE=0.50
VERSION='8.9.1'

WATCHDOG_SAME_SCREEN=24       # identische Screens bis Recovery (Battle ausgenommen)
WATCHDOG_UNSUPPORTED=6        # Screens ohne Aktor (Filter/Invokerliste): schneller reagieren
QUEST_MATCH_MIN=0.72
EVENT_TTL=180                 # Sekunden, danach gilt ein Event als nicht mehr bestätigt
REPLAY_SOFT_MAX=5             # Wiederholungen eines Quest-Levels, danach Quest per OCR neu pruefen
REPLAY_HARD_MAX=10            # absolute Grenze, auch wenn kein ZURUECK-Button erkannt wird
