#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path
from videoprocessing.generate_sprite import process_single_video, DEFAULT_INTERVAL, DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_QUALITY, DEFAULT_VTT_MODE, DEFAULT_IMAGE_FORMAT, DEFAULT_IMAGE_QUALITY, DEFAULT_COLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_video_files(videos_dir: Path) -> list[Path]:
    """Find all video files in a directory."""
    video_extensions = ['.mp4', '.webm', 'mov', '.mkv', '.avi']
    return [p for p in videos_dir.rglob("*") if p.suffix.lower() in video_extensions]

def generate_sprites_for_all_videos(
    videos_dir: Path,
    output_dir: Path,
    interval: int,
    width: int,
    height: int,
    quality: int,
    vtt_mode: str,
    image_format: str,
    image_quality: int,
    cols: int,
):
    """Generate sprite thumbnails for all videos in a directory."""
    if not videos_dir.is_dir():
        logging.error(f"Videos directory not found: {videos_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    video_files = get_video_files(videos_dir)

    if not video_files:
        logging.warning("No video files found in the specified directory")
        return

    logging.info(f"Found {len(video_files)} video files")

    for video_file in video_files:
        logging.info(f"Processing: {video_file.name}")
        try:
            process_single_video(
                input_path=video_file,
                outdir=output_dir,
                cols=cols,
                rows_opt=None,
                width=width,
                height=height,
                interval=interval,
                quality=quality,
                vtt_mode=vtt_mode,
                image_format=image_format,
                image_quality=image_quality,
            )
            logging.info(f"✓ Successfully processed: {video_file.name}")
        except Exception as e:
            logging.error(f"✗ Failed to process {video_file.name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate sprites for all videos in a directory.")
    parser.add_argument("--videos_dir", type=str, required=True, help="Directory containing video files.")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save the generated sprites.")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Interval in seconds between thumbnails.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Width of each thumbnail.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Height of each thumbnail.")
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY, help="FFmpeg/WebP quality.")
    parser.add_argument("--vtt-mode", type=str, default=DEFAULT_VTT_MODE, choices=["sprite", "tiles"], help="VTT mode.")
    parser.add_argument("--image-format", type=str, default=DEFAULT_IMAGE_FORMAT, choices=["webp", "jpg", "png"], help="Image format.")
    parser.add_argument("--image-quality", type=int, default=DEFAULT_IMAGE_QUALITY, help="Image quality (1-100).")
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS, help="Number of columns in the sprite sheet.")

    args = parser.parse_args()

    generate_sprites_for_all_videos(
        videos_dir=Path(args.videos_dir),
        output_dir=Path(args.output_dir),
        interval=args.interval,
        width=args.width,
        height=args.height,
        quality=args.quality,
        vtt_mode=args.vtt_mode,
        image_format=args.image_format,
        image_quality=args.image_quality,
        cols=args.cols,
    )

if __name__ == "__main__":
    main()