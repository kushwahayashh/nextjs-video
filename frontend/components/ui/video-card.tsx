import { VideoMetadata } from "@/lib/types";
import { formatFileSize, formatDuration } from "@/lib/utils";
import Image from "next/image";
import { useState, useCallback } from "react";
import { ContextMenu } from "@/components/ui/context-menu";
import { MoreVertical, Image as ImageIcon } from "lucide-react";
import { useRouter } from "next/navigation";

interface VideoCardProps {
  video: VideoMetadata;
}

export function VideoCard({ video }: VideoCardProps) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isGenerating, setIsGenerating] = useState(false);

  const handlePlay = useCallback(() => {
    if (!video.videoUrl) return;
    const params = new URLSearchParams({
      src: video.videoUrl,
      title: video.title,
      file: video.fileName,
    });
    router.push(`/player?${params.toString()}`);
  }, [router, video.fileName, video.title, video.videoUrl]);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setMenuPos({ x: e.clientX, y: e.clientY });
    setMenuOpen(true);
  }, []);

  const generateSprite = useCallback(async () => {
    if (isGenerating) return;
    try {
      setIsGenerating(true);
      const res = await fetch("/api/sprite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fileName: video.fileName }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        console.error("Sprite generation failed", data);
        return;
      }
      console.log("Sprite generation triggered for", video.fileName);
    } catch (err) {
      console.error("Failed to trigger sprite generation", err);
    } finally {
      setIsGenerating(false);
    }
  }, [isGenerating, video.fileName]);

  return (
    <div
      className="relative overflow-hidden rounded-xl border bg-card shadow-sm cursor-pointer transition-shadow hover:shadow-md group"
      onClick={handlePlay}
      onContextMenu={handleContextMenu}
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
      {/* Context menu trigger icon (visible on hover) */}
      <button
        aria-label="More options"
        className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity bg-popover/80 hover:bg-popover text-popover-foreground rounded-md p-1"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setMenuPos({ x: e.clientX, y: e.clientY });
          setMenuOpen(true);
        }}
      >
        <MoreVertical className="h-4 w-4" />
      </button>
      <div className="p-4 space-y-2" onClick={(e) => { e.stopPropagation(); }}>
        <h3 className="font-semibold line-clamp-2 text-sm leading-tight text-card-foreground" title={video.title}>
          {video.title}
        </h3>
        <div className="text-xs text-muted-foreground">
          {formatFileSize(video.size)}
        </div>
      </div>
      {menuOpen && (
        <ContextMenu
          items={[
            {
              id: "generate-sprite",
              label: isGenerating ? "Generating…" : "Generate sprite",
              icon: <ImageIcon className="h-4 w-4" />,
              onClick: generateSprite,
              disabled: isGenerating,
            },
          ]}
          position={menuPos}
          onClose={() => setMenuOpen(false)}
        />
      )}

      {isGenerating && (
        <div
          aria-live="polite"
          className="fixed left-1/2 -translate-x-1/2 bottom-6 z-[60] pointer-events-none"
        >
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg shadow-lg bg-popover text-popover-foreground border">
            <svg className="h-4 w-4 animate-spin text-muted-foreground" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            <span className="text-sm font-medium">Generating thumbnail</span>
          </div>
        </div>
      )}
    </div>
  );
}