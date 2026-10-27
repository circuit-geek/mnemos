import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Film, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { VideoCard } from "@/components/common/VideoCard";
import { ProcessingProgress } from "@/components/common/ProcessingProgress";
import { EmptyState } from "@/components/common/EmptyState";
import { videoService } from "@/services/videoService";

export default function VideoLibrary() {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const videos = useQuery({
    queryKey: ["videos"],
    queryFn: () => videoService.listVideos(),
    refetchInterval: (q) => (q.state.data?.some((v) => v.status === "processing") ? 250 : false),
  });
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => videoService.listJobs(),
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === "processing") ? 250 : false),
  });

  const upload = useMutation({
    mutationFn: (file: File) => videoService.uploadVideo(file),
    onSuccess: () => {
      setUploadError(null);
      void queryClient.invalidateQueries({ queryKey: ["videos"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (e: Error) => setUploadError(e.message),
  });

  const activeJobs = (jobs.data ?? []).filter((j) => j.status === "processing");
  const titleFor = (id: string) => videos.data?.find((v) => v.id === id)?.title ?? "Upload";

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
          <div className="flex flex-wrap items-center gap-3">
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
            <Button variant="primary" size="lg" onClick={() => inputRef.current?.click()}>
              <Upload className="size-4" /> Upload Video
            </Button>
            <span className="text-xs text-muted">
              MP4, MOV or WebM · stays in your browser · processing is a demo simulation
            </span>
          </div>
          {uploadError && (
            <p role="alert" className="flex items-center gap-2 text-sm text-warning">
              <AlertCircle className="size-4" /> {uploadError}
            </p>
          )}
        </header>

        {activeJobs.length > 0 && (
          <div className="flex flex-col gap-3">
            {activeJobs.map((job) => (
              <ProcessingProgress key={job.id} job={job} title={titleFor(job.videoId)} />
            ))}
          </div>
        )}

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
