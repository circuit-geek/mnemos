# 0002: What to track is decided per video, by Muse Spark unless the uploader says

Status: accepted (2026-10-31)

## Context

The SAM script tracks one noun phrase per run and labels every track with it, so one run can
only follow one kind of object, and spatial relations need several. A fixed list of concepts for
the whole deployment does not fit videos whose environments and objects differ.

## Decision

- SAM runs once per concept and the tracks are merged; tracking IDs are prefixed with the concept
  (`mug-0`) because IDs are only unique within a run.
- Concepts are chosen per video: the upload's optional `concepts` field wins; otherwise Muse Spark
  looks at frames sampled across the whole video and names the objects (`ConceptDiscoverer`).
  There is no global concept setting. If discovery finds nothing, SAM falls back to `object`.
- The requested and the tracked concepts are stored on the video and returned by the API.
- Discovery output is cleaned before use: names are lowercased, deduplicated, limited in length and
  count (`SAM_MAX_CONCEPTS`), and surfaces and body parts are dropped.

## Consequences

- Cost and time scale with the number of concepts (one SAM run each), hence the cap.
- Discovery is a model call and is not deterministic: it can add an object that is not there
  (an empty SAM run) or miss a small one. Uploaders can name the objects to avoid this.
- A concept with no detections produces no tracks and is not an error.
- Identity can still split across a long occlusion (the same mug may become two tracks).
