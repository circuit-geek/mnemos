# Demo / Test Videos

Five short clips (15–20 s each) that together exercise every query intent. They double as backend
integration fixtures and as the demo videos in the UI. Filmed, not generated: SAM and Muse need real
objects, and judges will see these.

## Shooting rules (all clips)

- **Static camera** (tripod or phone propped up). No panning or zoom: box movement must mean object movement.
- Landscape, 720p or 1080p, H.264 `.mp4`, 15–20 s, under 50 MB. Even lighting, plain desk, no clutter.
- Use **visually distinct, common objects** SAM can name: mug, notebook, laptop, phone, pen, cup, book, bag.
- One action every 3–5 s, in the order of the script. Keep your hands in frame only when the script says so.
- Save as `backend/test_data/demo_<n>_<name>.mp4`. Run each through the pipeline once and note the
  object labels and tracking IDs SAM produced (they decide which questions work).

## Clips

### 1. `demo_1_appearance` — what changed, and what was there before
Covers: `CHANGES`, `SCENE_AT_TIME`, `APPEARED`, "before the notebook appeared".
| Time | Action |
|---|---|
| 0–5 s | Desk with only a mug and a pen. Nothing moves. |
| 5 s | Place a notebook on the desk. |
| 10 s | Place a phone next to the notebook. |
| 10–18 s | Hands out of frame; nothing moves. |

Questions: "What changed in this video?" · "Which objects were on the desk before the notebook appeared?" ·
"What was on the desk at 0:03?" · "When did the phone appear?"

### 2. `demo_2_leaves_and_returns` — last seen, temporary loss
Covers: `LAST_SEEN`, `OBJECT_HISTORY`, `NO_LONGER_VISIBLE`, gap handling.
| Time | Action |
|---|---|
| 0–4 s | Laptop and mug on the desk. |
| 4 s | Pick up the mug and take it fully out of frame. |
| 4–12 s | Mug absent. Laptop stays. |
| 12 s | Put the mug back in a **different spot**. |
| 12–18 s | Nothing moves. |

Questions: "Where was the mug last seen?" · "When did the mug disappear from view?" ·
"What happened to the mug?" · "Where is the mug at the end?" (answers must say *no longer detected*, not *gone*).

### 3. `demo_3_occlusion` — absence is not disappearance
Covers: caveat handling, uncertainty, `NO_LONGER_VISIBLE` on an object that never left.
| Time | Action |
|---|---|
| 0–4 s | Mug and phone visible. |
| 4 s | Slide a large book in front of the phone so it is fully hidden. |
| 4–12 s | Book stays; phone hidden behind it. Mug stays visible. |
| 12 s | Slide the book away to reveal the phone. |
| 12–18 s | Nothing moves. |

Questions: "When was the phone last seen?" · "Did the phone leave the desk?" (expected: cannot be confirmed).

### 4. `demo_4_rearrange` — movement and spatial relations
Covers: `MOVED`, `RELATIONSHIPS` (`NEXT_TO`, `NEAR`, `ON`), relationship change over time.
| Time | Action |
|---|---|
| 0–4 s | Notebook flat in the middle; pen to its left; mug far right. |
| 4 s | Move the pen to the right of the notebook. |
| 9 s | Place the mug **on top of** the notebook. |
| 13–18 s | Nothing moves. |

Questions: "What is the mug on?" · "What was next to the pen at the start?" · "Which objects moved?" ·
"How did the layout change?"

### 5. `demo_5_containers` — inside / contains
Covers: `RELATIONSHIPS` (`INSIDE`, `CONTAINS`), objects hidden by a container.
| Time | Action |
|---|---|
| 0–4 s | Empty open bag (or a large cup) and a pen on the desk. |
| 4 s | Put the pen **inside** the bag/cup so the top stays visible. |
| 10 s | Take the pen out and leave it on the desk. |
| 14–18 s | Nothing moves. |

Questions: "Where was the pen between 0:05 and 0:09?" · "What was inside the bag?" · "When was the pen taken out?"

## Acceptance

A clip is accepted when, after processing: SAM tracks each named object under one stable tracking ID (or the
split is noted), the events list matches the script timing within about 1 s, and each listed question gets a
grounded answer or an explicit insufficient-evidence reply. Clips 4 and 5 need spatial relationships;
until those exist, they are accepted on temporal questions only.
