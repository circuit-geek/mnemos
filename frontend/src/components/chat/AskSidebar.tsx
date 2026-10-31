import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MessageSquareText, Send, X } from "lucide-react";
import { useExplorer } from "@/hooks/ExplorerContext";
import { reasoningService } from "@/services/reasoningService";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ReasoningMessage } from "@/types";
import { MessageBubble } from "./MessageBubble";

let counter = 0;
const nextId = () => `msg-${Date.now()}-${counter++}`;

export function AskSidebar({ onClose }: { onClose: () => void }) {
  const { video, memory } = useExplorer();
  const [messages, setMessages] = useState<ReasoningMessage[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const suggestions = useMemo(() => reasoningService.suggestedQuestions(memory.objects), [memory.objects]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  const ask = useCallback(
    async (question: string, addUserMessage = true) => {
      const q = question.trim();
      if (!q || pending) return;
      if (addUserMessage) {
        setMessages((m) => [...m, { id: nextId(), role: "user", content: q, createdAt: new Date().toISOString() }]);
      }
      setPending(true);
      try {
        const res = await reasoningService.ask(video.id, q, memory);
        setMessages((m) => [
          ...m,
          {
            id: nextId(),
            role: "assistant",
            content: res.answer,
            createdAt: new Date().toISOString(),
            unsupported: !res.supported,
            intent: res.intent ?? undefined,
            evidence: res.evidence,
            referencedObjectIds: res.referencedObjectIds,
          },
        ]);
      } catch (e) {
        setMessages((m) => [
          ...m,
          {
            id: nextId(),
            role: "assistant",
            content: e instanceof Error ? e.message : "The request failed.",
            createdAt: new Date().toISOString(),
            error: true,
          },
        ]);
      } finally {
        setPending(false);
      }
    },
    [pending, video.id, memory],
  );

  const retry = (errorId: string) => {
    const idx = messages.findIndex((m) => m.id === errorId);
    const question = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")?.content;
    setMessages((m) => m.filter((x) => x.id !== errorId));
    if (question) void ask(question, false);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = input;
    setInput("");
    void ask(q);
  };

  return (
    <div className="flex h-full flex-col bg-surface">
      <header className="flex items-center gap-2 border-b border-line px-4 py-3">
        <MessageSquareText className="size-4 text-accent" aria-hidden />
        <h2 className="text-sm font-semibold">Ask MNEMOS</h2>
        <Badge tone="accent" className="ml-1">Muse Spark</Badge>
        <Button variant="ghost" size="icon" className="ml-auto lg:hidden" aria-label="Close Ask MNEMOS" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </header>

      <div ref={scrollRef} className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {messages.length === 0 && !pending && (
          <div className="flex flex-col gap-2 py-2 text-sm text-muted">
            <p className="font-medium text-fg">Ask about what changed in this recording.</p>
            <p className="text-xs leading-relaxed">
              Muse Spark answers from this video's stored memory and cites the evidence it used. Click evidence
              to jump to that moment in the video and graph.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} onRetry={m.error ? () => retry(m.id) : undefined} />
        ))}
        {pending && (
          <div role="status" className="fade-in mr-4 flex items-center gap-2 self-start rounded-2xl rounded-bl-md border border-line bg-elevated px-3.5 py-3 text-xs text-muted">
            <span className="flex gap-1" aria-hidden>
              {[0, 150, 300].map((d) => (
                <span key={d} className="size-1.5 animate-pulse rounded-full bg-accent" style={{ animationDelay: `${d}ms` }} />
              ))}
            </span>
            Searching memory…
          </div>
        )}
      </div>

      <div className="border-t border-line p-3">
        <ul className="mb-2 flex flex-wrap gap-1.5" aria-label="Suggested questions">
          {suggestions.map((q) => (
            <li key={q}>
              <button
                type="button"
                disabled={pending}
                onClick={() => void ask(q)}
                className="rounded-full border border-line bg-elevated px-2.5 py-1 text-left text-xs text-fg transition-colors hover:border-accent/60 disabled:opacity-50"
              >
                {q}
              </button>
            </li>
          ))}
        </ul>
        <form onSubmit={submit} className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this recording…"
            aria-label="Ask a question"
            className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-elevated px-3 text-sm placeholder:text-muted"
          />
          <Button type="submit" variant="primary" size="icon" className="size-9" disabled={pending || !input.trim()} aria-label="Send question">
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
