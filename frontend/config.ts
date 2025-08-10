export interface AppConfig {
  /** Parent folder containing subfolders: `videos`, `thumbnails`, `processed` */
  storageDir: string;
}

// Minimal configuration: storage directory only
export const config: Readonly<AppConfig> = {
  storageDir: process.env.MEDIA_STORAGE_DIR || "/teamspace/studios/this_studio/filen",
} as const;