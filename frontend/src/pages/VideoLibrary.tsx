import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Film, Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VideoCard } from "@/components/common/VideoCard";
import { EmptyState } from "@/components/common/EmptyState";
import { videoService } from "@/services/videoService";

export default function VideoLibrary() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [concepts, setConcepts] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);

  const videos = useQuery({
    queryKey: ["videos"],
    queryFn: () => videoService.listVideos(),
    refetchInterval: (q) => (q.state.data?.some((v) => v.status === "processing") ? 2000 : false),
  });

  const upload = useMutation({
    mutationFn: (file: File) => videoService.uploadVideo(file, concepts),
    onSuccess: (videoId) => {
      setUploadError(null);
      void queryClient.invalidateQueries({ queryKey: ["videos"] });
      // Watch the pipeline work: the explorer shows live progress, then opens the results.
      navigate(`/explore/${videoId}`);
    },
    onError: (e: Error) => setUploadError(e.message),
  });

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-5 py-10 sm:px-8 lg:py-14">
        <header className="flex flex-col gap-5">
          <div>
            <h1 className="text-3xl font-semibold tracking-[0.14em] sm:text-4xl">MNEMOS</h1>
            <p className="mt-2 text-lg text-accent">Giving AI a memory of the physical world.</p>
          </div>
          <p className="max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
            Transform video observations into persistent memories. Explore objects, track
            relationships through time, and ask questions about what changed.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <input
              ref={inputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
              className="sr-only"
              tabIndex={-1}
              aria-label="Choose a video file"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate(file);
                e.target.value = "";
              }}
            />
            <label className="flex w-full flex-col gap-1 text-xs text-muted sm:max-w-sm">
              Objects to track <span className="text-muted/80">(optional, comma-separated; blank = detect automatically)</span>
              <input
                value={concepts}
                onChange={(e) => setConcepts(e.target.value)}
                placeholder="e.g. mug, notebook, pen"
                maxLength={200}
                disabled={upload.isPending}
                className="h-10 rounded-lg border border-line bg-elevated px-3 text-sm text-fg placeholder:text-muted"
              />
            </label>
            <Button
              variant="primary"
              size="lg"
              disabled={upload.isPending}
              onClick={() => inputRef.current?.click()}
            >
              {upload.isPending ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
              {upload.isPending ? "Uploading…" : "Upload Video"}
            </Button>
          </div>
          <p className="text-xs text-muted">MP4, MOV or WebM · analyzed by SAM 3.1 and Muse Spark</p>
          {uploadError && (
            <p role="alert" className="flex items-center gap-2 text-sm text-warning">
              <AlertCircle className="size-4" /> {uploadError}
            </p>
          )}
        </header>

        <section aria-labelledby="recordings-heading" className="flex flex-col gap-4">
          <h2 id="recordings-heading" className="text-sm font-medium uppercase tracking-wider text-muted">
            Recordings
          </h2>
          {videos.isPending ? (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-80" />
              ))}
            </div>
          ) : videos.isError ? (
            <EmptyState
              icon={<AlertCircle className="size-5" />}
              title="Couldn't load recordings"
              description={videos.error.message}
              action={<Button onClick={() => void videos.refetch()}>Try again</Button>}
            />
          ) : videos.data.length === 0 ? (
            <EmptyState
              icon={<Film className="size-5" />}
              title="No recordings yet"
              description="Upload a video to start building a visual memory."
            />
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {videos.data.map((v) => (
                <VideoCard key={v.id} video={v} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
