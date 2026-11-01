# Demo clips

Three short handheld recordings used for the demo and as reference input. Upload any of them in the
UI (leave "Objects to track" empty and MNEMOS finds the objects itself), or with curl:

```bash
curl -F "file=@demo/scenario_2.mp4;type=video/mp4" localhost:8000/api/v1/videos
```

| Clip | Length | What happens | Try asking |
|---|---|---|---|
| `scenario_1.mp4` | 21 s | A mug sits next to a laptop, leaves view for about five seconds, and comes back | "Where was the mug last seen?", "What happened to the mug?" |
| `scenario_2.mp4` | 19 s | A mug and pen; a notebook arrives at 8 s and a phone at 15 s | "What is next to the notebook?", "Which objects were on the desk before the notebook appeared?", "How is the scene different at the end compared to the start?" |
| `scenario_3.mp4` | 23 s | A pen beside a notebook; a mug is placed on the notebook at about 20 s | "What is the mug on?", "What changed between 15 and 22 seconds?" |

The camera is handheld, so still objects can appear to move; MNEMOS reports movement "in the frame".
Processing takes one to two minutes per clip and needs a Meta API key (see the root README).
Recorded answers for these clips are used by the tests in `backend/fixtures/scenarios`.
