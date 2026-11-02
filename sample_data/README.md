# Sample data

Short clips to try MNEMOS without recording your own. All three are 854x480 and 16-24 seconds long, filmed from above on the same desk with the same objects: a pen, a book (*The Iliad*), a mug and a phone.

MNEMOS takes video only. Upload one in the app (or `POST /videos`) and leave the objects field empty: Muse Spark picks what to track, SAM 3.1 tracks it, and the scene is stored as a temporal graph you can ask questions about.

| File | Length | What happens in the clip |
|---|---|---|
| `scenario_1.mp4` | ~16 s | The simplest case: a pen and a book on the desk. A hand reaches in and moves the pen, then leaves; the book stays put. |
| `scenario_2.mp4` | ~19 s | A pen and a book at the start. A hand moves the pen, then a mug is brought in and ends up on the book. |
| `scenario_3.mp4` | ~24 s | A pen, a mug and a book. A phone is placed on the desk between the mug and the book, the pen is put in the mug, and the phone is finally placed on the book. |

## Questions to try

- Where was the pen last seen?
- What changed in this video?
- What is next to the book?
- Is the mug on the book?
- How is the scene different at the end compared to the start?
- When did the mug appear?

The answers come from the stored graph and cite the frames they rest on. If the clip does not contain the answer, MNEMOS says the evidence is insufficient instead of guessing.

## Notes

- Objects that are handled or occluded by the hand may show a "no longer detected" interval. That is a visibility gap, not proof the object left.
- Processing calls the Meta Model API (SAM 3.1 and Muse Spark), so `META_API_KEY` must be set. See `backend/.env.example`.
