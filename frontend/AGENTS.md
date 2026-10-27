# MNEMOS Frontend — Agent Development Instructions

## 1. Frontend Overview

MNEMOS is a visual memory platform that enables users to explore how physical environments change over time.

The frontend provides an interactive interface for:

- Uploading and processing video recordings.
- Viewing detected objects.
- Exploring temporal knowledge graphs.
- Navigating historical observations.
- Inspecting memory events.
- Asking natural-language questions.
- Viewing visual evidence associated with answers.

The interface must make the system's memory understandable and interactive.

Follow the repository-wide instructions in the root `AGENTS.md`.

---

## 2. Primary Product Experience

The main MNEMOS experience consists of three connected capabilities:

### Visual Perception

Shows the video and detected objects.

### Temporal Memory

Shows the knowledge graph and historical relationships.

### Reasoning

Allows users to query memory through natural language.

All three capabilities must remain synchronized.

The central product interaction is navigating time and observing how the graph changes.

---

## 3. State Management

The application contains several components that depend on the same video timestamp.

These include:

- Video player.
- Detection overlays.
- Temporal knowledge graph.
- Event timeline.
- Object inspector.
- Evidence viewer.
- Reasoning sidebar.

### Shared Timeline State

Maintain a single authoritative selected timestamp.

All components must use this shared timestamp.

Do not maintain independent, conflicting playback positions across components.

When the timestamp changes:

1. Update video playback position.
2. Retrieve or calculate the graph state for that timestamp.
3. Update visible object observations.
4. Update active relationships.
5. Highlight relevant timeline events.

Use existing hooks or state-management conventions.

Do not introduce global state libraries unless the current architecture requires them.

---

## 4. Video Player

The video player must support:

- Play.
- Pause.
- Seeking.
- Playback speed.
- Current timestamp.
- Total duration.
- Detection overlays.
- Evidence navigation.

### Detection Overlays

Bounding boxes must use normalized coordinates or be transformed consistently from their source dimensions.

Overlay positions must account for video scaling and letterboxing.

Detected objects should be selectable.

Selecting an object should synchronize the selection with the temporal graph.

Use stable object identifiers.

Do not create object IDs from array indices.

If no detection exists at a timestamp, display an appropriate state rather than reusing stale detections.

---

## 5. Temporal Knowledge Graph

Use the existing React Flow implementation.

Graph nodes represent objects or semantic locations.

Graph edges represent relationships.

### Node Requirements

Each node should contain:

- Stable object ID.
- Semantic label.
- Object or location type.
- Selection state.
- Visibility state where applicable.

### Edge Requirements

Each edge should contain:

- Relationship ID.
- Source node ID.
- Target node ID.
- Relationship type.
- Validity interval.
- Evidence reference where available.

### Temporal Behavior

Render the graph state corresponding to the selected timestamp.

When seeking backward, historical relationships should reappear if they were valid at that time.

When seeking forward, inactive relationships should no longer be displayed as active.

Do not delete historical relationships from frontend memory merely because they are inactive in the current view.

### Graph Interaction

Support:

- Node selection.
- Zoom.
- Pan.
- Fit to view.
- Object inspection.
- Relationship inspection where available.

Avoid unnecessary graph re-layout during every playback update.

Preserve graph positions where possible.

---

## 6. Object Inspector

Selecting an object should display relevant memory information.

Include:

- Object ID.
- Object label.
- First observed timestamp.
- Last observed timestamp.
- Current visibility.
- Last known location.
- Relationship history.
- Evidence timestamps.

Historical observations must be clickable.

Clicking an observation should navigate the shared timeline to that timestamp.

If information is unavailable, display an explicit unknown state.

Do not invent object attributes.

---

## 7. Memory Timeline

The timeline represents the temporal history of a recording.

It must support:

- Seeking to timestamps.
- Event markers.
- Previous event.
- Next event.
- Active event selection.
- Synchronization with graph and video.

### Event Types

Initial event types include:

- `OBJECT_APPEARED`
- `OBJECT_NOT_VISIBLE`
- `OBJECT_MOVED`
- `RELATIONSHIP_CHANGED`

Events must be sourced from backend data when the real integration is enabled.

Do not generate arbitrary events in the frontend.

Each event should display:

- Timestamp.
- Event type.
- Description.
- Referenced objects.
- Evidence availability.

---

## 8. Ask MNEMOS

The reasoning interface allows users to ask questions about historical observations.

### Responsibilities

- Accept natural-language queries.
- Display query processing state.
- Render answers.
- Display evidence references.
- Support navigation to referenced timestamps.
- Handle unsupported questions and errors.

Suggested questions:

- What changed in this scene?
- Where was the mug last seen?
- Which objects were on the desk initially?
- What happened between 10 and 20 seconds?

### Evidence Navigation

When a user clicks an evidence reference:

1. Seek the video to the evidence timestamp.
2. Update the temporal graph.
3. Highlight the referenced object or event.
4. Display the relevant evidence frame when available.

This behavior is a core product requirement.

### Answer Integrity

Do not fabricate AI responses.

When using mock data, clearly identify the application as a prototype or demo.

When connected to the backend, display actual API responses.

Do not silently fall back to mock reasoning when a live API request fails.

---

## 9. API Integration

The backend is implemented using FastAPI.

All backend communication must be organized through service modules.

Do not place API requests directly inside presentational components.

Consult `docs/api/contracts.md` before implementing API integration.

These endpoints are proposed contracts until documented and implemented.

### Integration Rules

- Centralize API configuration.
- Use typed request and response models.
- Handle network errors.
- Handle loading and empty states.
- Handle processing failures.
- Avoid duplicate API requests.
- Clean up subscriptions and asynchronous effects.
- Cancel or ignore stale requests when timestamps change rapidly.

Configure the API base URL through:

`VITE_API_BASE_URL`

Never expose private API credentials in frontend code.


## 10. Frontend Deployment

The frontend must remain independently deployable.
Do not assume the backend and frontend share the same domain.

---