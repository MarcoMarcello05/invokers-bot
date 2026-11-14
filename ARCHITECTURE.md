# ARCHITECTURE
Window geometry + local structured state (next phase) + DXcam/MSS frame -> vision -> stable-state gate -> policy -> safety gate -> Windows input -> re-observe.

Rules:
- UNKNOWN never clicks.
- Prefer template targets over guessed coordinates.
- Any coordinates are client-normalized.
- F12 abort.
- Purchase-like actions blocked by default.
- Persistent UNKNOWN saves diagnostics.
- Perception, policy and input stay separated.
