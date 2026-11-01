# 0004: Re-link split tracks only when it is unambiguous

Status: accepted (2026-11-01)

## Context

SAM assigns a new tracking ID when an object leaves view and returns. In `scenario_1` one mug became
two "objects", so "where was the mug last seen?" answered 9.7 s even though it came back and stayed
until the end. The root `AGENTS.md` asks for conservative identity association and explicit
uncertainty, and says not to merge objects merely because they share a category.

## Decision

After SAM, merge same-label tracks only when all of these hold: they never overlap in time; the gap is
at most 8 s; and no other track with that label is visible during the gap, so the returning object cannot be a
different instance. Chains (leaves, returns, leaves, returns) merge into one. Otherwise tracks stay
separate. The merge keeps the first track's ID, is logged, and is stored on the object
(`linked_tracking_ids`). The gap remains visible as a `NO_LONGER_VISIBLE` event.

## Consequences

- One mug that leaves and returns is one object; the gap is reported as "no longer detected", never as
  proof it left.
- Two similar objects (two mugs) or long absences are never merged; those remain separate objects.
- A rare wrong merge is possible if a different object of the same label replaces the original while the
  original is out of view. The conditions make that unlikely, and the answering prompt still calls
  identities "not verified physical identities".
- No model call is used; the rule is deterministic and unit tested (`tests/test_identity.py`).
