import { mockLatency } from "@/lib/api";
import { DEMO_VIDEO_ID } from "@/mocks/objects";
import { UNSUPPORTED_ANSWER, matchQuestion, suggestedQuestions } from "@/mocks/reasoning";
import type { AskResponse } from "@/types";

export const reasoningService = {
  suggestedQuestions(): string[] {
    return suggestedQuestions;
  },

  /**
   * POST /api/v1/videos/{videoId}/ask
   * Mock: deterministic answers for a fixed set of questions. No LLM is called.
   */
  async ask(videoId: string, question: string): Promise<AskResponse> {
    await mockLatency(null, 900);
    if (videoId !== DEMO_VIDEO_ID) {
      throw new Error(
        "No memory data is available for this recording. The prototype has no backend to analyze uploads.",
      );
    }
    const match = matchQuestion(question);
    if (match) return match;
    return {
      answer: UNSUPPORTED_ANSWER,
      supported: false,
      evidence: [],
      referencedObjectIds: [],
    };
  },
};
