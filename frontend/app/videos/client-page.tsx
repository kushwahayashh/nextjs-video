"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { VideoMetadata } from "@/lib/types";
import { VideoLibrary as VideoLibraryComponent } from "@/components/ui/video-library";
import { getAllVideos } from "@/lib/actions";

export default function VideosPage() {
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const searchParams = useSearchParams();
  const query = (searchParams.get("q") ?? "").trim().toLowerCase();

  useEffect(() => {
    async function fetchVideos() {
      try {
        const data = await getAllVideos();
        setVideos(data);
      } catch (error) {
        console.error('Error fetching videos:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchVideos();
  }, []);

  const filteredVideos = useMemo(() => {
    if (!query) return videos;
    return videos.filter(v => {
      const title = (v.title ?? "").toLowerCase();
      const fileName = (v.fileName ?? "").toLowerCase();
      return title.includes(query) || fileName.includes(query);
    });
  }, [videos, query]);

  return (
    <main className="min-h-screen bg-background">
      <VideoLibraryComponent
        videos={filteredVideos}
        loading={loading}
      />
    </main>
  );
}