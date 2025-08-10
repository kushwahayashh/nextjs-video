import { VideoMetadata } from "@/lib/types";
import { formatFileSize, formatDuration } from "@/lib/utils";
import Image from "next/image";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

interface VideoCardProps {
  video: VideoMetadata;
}

export function VideoCard({ video }: VideoCardProps) {
  const router = useRouter();

  const handlePlay = useCallback(() => {
    if (!video.videoUrl) return;
    const params = new URLSearchParams({
      src: video.videoUrl,
      title: video.title,
      file: video.fileName,
    });
    router.push(`/player?${params.toString()}`);
  }, [router, video.fileName, video.title, video.videoUrl]);

  return (
    <div
      className="relative overflow-hidden rounded-xl border bg-card shadow-sm cursor-pointer transition-shadow hover:shadow-md"
      onClick={handlePlay}
    >
      <div className="aspect-video relative overflow-hidden bg-muted">
        {video.thumbnailUrl ? (
          <Image
            src={video.thumbnailUrl}
            alt={video.title}
            fill
            className="object-cover"
          />
        ) : (
          <div className="flex items-center justify-center h-full bg-gradient-to-br from-muted to-background">
            <p className="text-xs text-muted-foreground">No thumbnail</p>
          </div>
        )}
        {/* Hover overlay */}
        <div className="pointer-events-none absolute inset-0 bg-black/0 opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-hover:bg-black/20" />
        {/* Video duration badge */}
        {video.duration && (
          <div className="absolute bottom-2 left-2 bg-popover/90 text-popover-foreground text-xs px-2 py-1 rounded font-medium z-10">
            {formatDuration(video.duration)}
          </div>
        )}
      </div>
      <div className="p-4 space-y-2" onClick={(e) => { e.stopPropagation(); }}>
        <h3 className="font-semibold line-clamp-2 text-sm leading-tight text-card-foreground" title={video.title}>
          {video.title}
        </h3>
        <div className="text-xs text-muted-foreground">
          {formatFileSize(video.size)}
        </div>
      </div>

    </div>
  );
}