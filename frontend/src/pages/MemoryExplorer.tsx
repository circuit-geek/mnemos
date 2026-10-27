import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, Clock, Loader2, PanelRight } from "lucide-react";
import { videoService } from "@/services/videoService";
import { memoryService } from "@/services/memoryService";
import { ExplorerProvider } from "@/hooks/ExplorerContext";
import { Wordmark } from "@/components/common/Logo";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VisualPerceptionPanel } from "@/components/video/VisualPerceptionPanel";
import { KnowledgeGraph } from "@/components/graph/KnowledgeGraph";
import { TimelinePanel } from "@/components/timeline/TimelinePanel";
import { EventList } from "@/components/timeline/EventList";
import { AskSidebar } from "@/components/chat/AskSidebar";
import { cn, formatTime } from "@/lib/utils";
import type { VideoRecord } from "@/types";

function Header({
  video,
  sidebarOpen,
  onToggleSidebar,
}: {
  video?: VideoRecord;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-surface px-3 sm:px-4">
      <Wordmark className="hidden sm:inline" />
      <span className="hidden h-4 w-px bg-line sm:block" aria-hidden />
      <h1 className="min-w-0 truncate text-sm font-medium">{video?.title ?? "Loading…"}</h1>
      {video && (
        <>
          <StatusBadge status={video.status} />
          <span className="hidden items-center gap-1 text-xs tabular-nums text-muted sm:flex">
            <Clock className="size-3.5" aria-hidden /> {formatTime(video.duration)}
          </span>
          {video.isDemo && (
            <Badge tone="warning" className="hidden md:inline-flex">
              Demo data
            </Badge>
          )}
        </>
      )}
      <div className="ml-auto flex items-center gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/">
            <ArrowLeft className="size-4" />
            <span className="hidden sm:inline">Back to Library</span>
            <span className="sr-only sm:hidden">Back to Library</span>
          </Link>
        </Button>
        <Button
          variant={sidebarOpen ? "secondary" : "outline"}
          size="sm"
          onClick={onToggleSidebar}
          aria-expanded={sidebarOpen}
          aria-controls="ask-sidebar"
        >
          <PanelRight className="size-4" />
          <span className="hidden sm:inline">Ask MNEMOS</span>
          <span className="sr-only sm:hidden">Toggle Ask MNEMOS</span>
        </Button>
      </div>
    </header>
  );
}

function LoadingWorkspace() {
  return (
    <div className="flex flex-col gap-4 p-4" aria-busy="true" aria-label="Loading recording">
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-[420px]" />
        <Skeleton className="h-[420px]" />
      </div>
      <Skeleton className="h-40" />
    </div>
  );
}

export default function MemoryExplorer() {
  const { videoId = "" } = useParams();
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 1280);

  const video = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => videoService.getVideo(videoId),
    refetchInterval: (q) => (q.state.data?.status === "processing" ? 300 : false),
  });
  const memory = useQuery({
    queryKey: ["memory", videoId],
    queryFn: () => memoryService.getMemory(videoId),
    enabled: video.data?.status === "ready",
    staleTime: Infinity,
  });

  let body: React.ReactNode;
  if (video.isError) {
    body = (
      <EmptyState
        icon={<AlertCircle className="size-5" />}
        title="Recording not found"
        description="It may have been removed, or an upload from an earlier session no longer exists."
        action={
          <Button asChild variant="primary" size="sm">
            <Link to="/">Back to Library</Link>
          </Button>
        }
      />
    );
  } else if (video.isPending) {
    body = <LoadingWorkspace />;
  } else if (video.data.status === "processing") {
    body = (
      <EmptyState
        icon={<Loader2 className="size-5 animate-spin" />}
        title="Still processing"
        description="This recording is being processed (simulated). The explorer opens when it's ready."
      />
    );
  } else if (video.data.status === "failed") {
    body = (
      <EmptyState
        icon={<AlertCircle className="size-5" />}
        title="Processing failed"
        description="This recording couldn't be processed."
      />
    );
  } else if (memory.isError) {
    body = (
      <EmptyState
        icon={<AlertCircle className="size-5" />}
        title="Couldn't load memory"
        action={<Button onClick={() => void memory.refetch()}>Try again</Button>}
      />
    );
  } else if (memory.isPending) {
    body = <LoadingWorkspace />;
  } else {
    body = (
      <ExplorerProvider key={video.data.id} video={video.data} memory={memory.data}>
        <div className="flex min-h-0 flex-1">
          <div className="min-w-0 flex-1 overflow-y-auto">
            <div className="flex min-h-full flex-col gap-4 p-3 sm:p-4">
              <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:min-h-[440px] lg:flex-1 lg:grid-cols-2">
                <VisualPerceptionPanel />
                <KnowledgeGraph />
              </div>
              <TimelinePanel />
              <EventList />
            </div>
          </div>
          <aside
            id="ask-sidebar"
            aria-label="Ask MNEMOS"
            inert={!sidebarOpen}
            className={cn(
              "shrink-0 overflow-hidden border-line bg-surface transition-[width,transform] duration-300 ease-out",
              "max-lg:fixed max-lg:inset-y-0 max-lg:right-0 max-lg:z-40 max-lg:w-[min(92vw,380px)] max-lg:border-l max-lg:shadow-2xl",
              sidebarOpen
                ? "max-lg:translate-x-0 lg:w-[380px] lg:border-l"
                : "max-lg:translate-x-full lg:w-0",
            )}
          >
            <div className="h-full w-[min(92vw,380px)] lg:w-[380px]">
              <AskSidebar onClose={() => setSidebarOpen(false)} />
            </div>
          </aside>
        </div>
      </ExplorerProvider>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <Header
        video={video.data}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((o) => !o)}
      />
      {body}
    </div>
  );
}
