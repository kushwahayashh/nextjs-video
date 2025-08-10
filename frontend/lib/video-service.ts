import { readdir, stat, mkdir } from "fs/promises";
import { join } from "path";
import { config } from "@/config";
import { MIME_TYPES } from "@/lib/mime-types";
import { VideoMetadata } from "@/lib/types";
import { getFileExtension, getBaseName } from "@/lib/file-utils";

export class VideoService {
  private static readonly VIDEOS_DIR = join(config.storageDir, 'videos');
  private static readonly THUMBNAILS_DIR = join(config.storageDir, 'thumbnails');
  private static readonly PROCESSED_DIR = join(config.storageDir, 'processed');

  /** Ensure base directories exist */
  private static async ensureBaseDirs(): Promise<void> {
    try { await mkdir(this.VIDEOS_DIR, { recursive: true }); } catch {}
    try { await mkdir(this.THUMBNAILS_DIR, { recursive: true }); } catch {}
    try { await mkdir(this.PROCESSED_DIR, { recursive: true }); } catch {}
  }

  /**
   * Get video metadata for a single file
   */
  static async getVideoMetadata(file: string): Promise<VideoMetadata> {
    const filePath = join(this.VIDEOS_DIR, file);
    const fileStat = await stat(filePath);
    const baseName = getBaseName(file);

    const extension = getFileExtension(file);
    
    let duration: number | undefined;
    try {
      const metaPath = join(this.PROCESSED_DIR, `${baseName}_meta.json`);
      const metaContents = await stat(metaPath);
      const meta = JSON.parse(metaContents.toString());
      duration = meta.duration;
    } catch {
      // Ignore if metadata file doesn't exist
    }

    return {
      id: file,
      title: baseName.replace(/[_-]/g, ' '),
      fileName: file,
      size: fileStat.size,
      duration: duration,
      createdAt: fileStat.birthtime,
      thumbnailUrl: `/thumbnails/${baseName}.jpeg`, // Assume thumbnail exists
      videoUrl: `/videos/${file}`,
      mimeType: MIME_TYPES[extension] || 'video/mp4',
    };
  }

  /**
   * Get all videos metadata
   */
  static async getAllVideos(): Promise<VideoMetadata[]> {
    await this.ensureBaseDirs();
    const files = await readdir(this.VIDEOS_DIR);
    const videos: VideoMetadata[] = [];
    
    // Process files in parallel for better performance
    const videoPromises = files.map(async (file) => {
      const extension = getFileExtension(file);
      
      const supported = Object.prototype.hasOwnProperty.call(MIME_TYPES, extension);
      if (extension && supported) {
        try {
          return await this.getVideoMetadata(file);
        } catch {
          // Skip files that can't be processed
          return null;
        }
      }
      return null;
    });
    
    const results = await Promise.allSettled(videoPromises);
    
    for (const result of results) {
      if (result.status === 'fulfilled' && result.value) {
        videos.push(result.value);
      }
    }
    
    return videos;
  }
}