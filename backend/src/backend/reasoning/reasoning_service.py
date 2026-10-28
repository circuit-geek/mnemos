"""Question → validated intent → graph evidence → Muse-written, evidence-checked answer."""

import logging

from pydantic import ValidationError

from .models import Answer, Evidence, Intent, ModelAnswer, ModelResponseError, QueryIntent
from .retrieval import GraphRetriever

logger = logging.getLogger(__name__)

INTERPRET_INSTRUCTIONS = """You classify a user's question about a recorded video's object memory.
Return ONLY a JSON object: {"intent": ..., "object_label": string|null, "time_seconds": number|null,
"start_seconds": number|null, "end_seconds": number|null}.
Intents:
- LAST_SEEN: when/where an object was last seen, disappeared, vanished, left, went missing.
- OBJECT_HISTORY: what happened to an object overall, its timeline.
- CHANGES: what changed in the video or within a time window (set start/end seconds if given).
- SCENE_AT_TIME: what was happening at one specific moment (set time_seconds; object_label if one is named).
- RELATIONSHIPS: spatial relations between objects (on, next to, inside, near).
- UNSUPPORTED: anything else.
object_label must be one of known_objects (copy it exactly) or null. Convert times to seconds ("1:05" -> 65)."""

ANSWER_INSTRUCTIONS = """You answer questions about a video using ONLY the evidence items provided.
Return ONLY a JSON object: {"answer": string, "evidence_ids": [string], "sufficient_evidence": boolean}.
Rules:
- Cite the evidence_ids you relied on; never cite an id that was not provided.
- Times are seconds from the start of the recording.
- NO_LONGER_VISIBLE means the tracker stopped detecting the object. It is NOT proof the object physically
  disappeared or left; it may be occluded or missed. Say so, and use wording like "was no longer detected".
- Track identities are scoped to this recording and are not verified physical identities.
- sufficient_evidence is about whether the evidence answers the question as far as detection data allows.
  Report detection gaps with their caveat and keep sufficient_evidence true; only set it false when the
  evidence has nothing relevant to the question.
- If the evidence cannot answer the question, set sufficient_evidence to false and explain what is missing.
- Be concise (1-4 sentences). Do not invent details beyond the evidence."""


class ReasoningService:
    def __init__(self, repository, muse):
        self.retriever = GraphRetriever(repository)
        self.repository = repository
        self.muse = muse

    def interpret(self, video_id: str, question: str) -> QueryIntent:
        known = sorted({o["label"] for o in self.repository.get_video_objects(video_id)})
        raw = self.muse.generate_json(INTERPRET_INSTRUCTIONS,
                                      {"question": question, "known_objects": known})
        try:
            return QueryIntent.model_validate(raw)
        except ValidationError as error:
            raise ModelResponseError(f"Invalid query intent from model: {error}") from error

    def ask(self, video_id: str, question: str) -> Answer:
        intent = self.interpret(video_id, question)
        logger.info("video=%s intent=%s", video_id, intent.intent)
        retrieved = self.retriever.retrieve(video_id, intent)
        if retrieved.problem or not retrieved.evidence:
            return Answer(question=question, intent=intent, sufficient_evidence=False, evidence=[],
                          answer=retrieved.problem or "No matching memory was found.")
        raw = self.muse.generate_json(ANSWER_INSTRUCTIONS, {
            "question": question,
            "evidence": [e.model_dump(include={"evidence_id", "kind", "text"})
                         for e in retrieved.evidence]})
        try:
            model_answer = ModelAnswer.model_validate(raw)
        except ValidationError as error:
            raise ModelResponseError(f"Invalid answer from model: {error}") from error
        return self._validated(question, intent, model_answer, retrieved.evidence)

    @staticmethod
    def _validated(question: str, intent: QueryIntent, model_answer: ModelAnswer,
                   evidence: list[Evidence]) -> Answer:
        by_id = {e.evidence_id: e for e in evidence}
        cited = [by_id[i] for i in dict.fromkeys(model_answer.evidence_ids) if i in by_id]
        if model_answer.sufficient_evidence and not cited:
            return Answer(question=question, intent=intent, sufficient_evidence=False, evidence=[],
                          answer="The model's answer cited no retrieved evidence, so it was withheld. "
                                 f"Unverified draft: {model_answer.answer}")
        return Answer(question=question, intent=intent, answer=model_answer.answer,
                      sufficient_evidence=model_answer.sufficient_evidence, evidence=cited)
