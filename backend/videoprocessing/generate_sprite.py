#!/usr/bin/env python3
"""
High-quality thumbnail sprite & WebVTT generator.
Generates thumbnails every --interval seconds using parallel processing.
Outputs (depending on mode):
  sprite mode:
    - {outdir}/{base}_sprite.webp (configurable format)
    - {outdir}/{base}_sprite.vtt (references regions via #xywh)
  tiles mode:
    - {outdir}/{base}_tiles/tile_00000.webp (and subsequent tiles)
    - {outdir}/{base}_sprite.vtt (references individual tile files)
Requires ffmpeg & ffprobe in PATH.
"""

import argparse
import math
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Tuple
from PIL import Image
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Configure defaults here so the script can run with minimal or no arguments
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 180
DEFAULT_INTERVAL = 5
DEFAULT_QUALITY = 4  # FFmpeg/webp quality (lower is better). 2 is high quality
DEFAULT_IMAGE_FORMAT = "webp"
DEFAULT_IMAGE_QUALITY = 80  # Pillow WEBP quality
DEFAULT_VTT_MODE = "sprite"
DEFAULT_COLS = 10
DEFAULT_HWACCEL = "none"  # none|cuda|qsv|d3d11va
DEFAULT_EXTRACT_MODE = "single_pass"  # single_pass|seek_parallel


def probe_duration(input_path: Path) -> float:
    """
    Probes video duration using ffprobe.
    """
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


def format_timestamp(seconds: float) -> str:
    """
    Formats a timestamp in HH:MM:SS.mmm format.
    """
    ms = int((seconds - int(seconds)) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def extract_frame(input_path: Path, ts: float, size: Tuple[int, int], out: Path, quality: int, hwaccel: str = "none", image_format: str = "webp"):
    """
    Extracts a single frame at a specific timestamp.
    """
    width, height = size
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(ts),
    ]
    if hwaccel and hwaccel != "none":
        # Use hardware accel for decode when possible
        cmd += ["-hwaccel", hwaccel]

    output_options = []
    if image_format == "webp":
        output_options = ["-c:v", "libwebp", "-q:v", str(quality)]
    elif image_format == "jpeg":
        output_options = ["-c:v", "mjpeg", "-q:v", str(quality), "-pix_fmt", "yuvj420p"]

    cmd += [
        "-i", str(input_path),
        "-frames:v", "1",
        "-vf", f"scale={width}:{height}:flags=lanczos",
        *output_options,
        str(out),
        "-hide_banner", "-loglevel", "error"
    ]
    subprocess.run(cmd, check=True)


def extract_frames_parallel(input_path: Path, timestamps: List[float], size: Tuple[int, int], tmpdir: Path, quality: int, hwaccel: str = "none", image_format: str = "webp") -> List[Path]:
    """
    Extracts frames in parallel using a thread pool.
    """
    start_time = time.time()
    frames = []
    total = len(timestamps)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for idx, ts in enumerate(timestamps):
            out = tmpdir / f"frame_{idx:05d}.{image_format}"
            futures[executor.submit(extract_frame, input_path, ts, size, out, quality, hwaccel, image_format)] = idx
            frames.append(out)
        for i, future in enumerate(as_completed(futures)):
            if (i + 1) % (total // 10 or 1) == 0:
                logging.info(f"Extracting frames: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
    total_time = time.time() - start_time
    logging.info(f"Extracting frames: done in {total_time:.1f}s")
    return frames


def build_sprite(
    frames: List[Path],
    cols: int,
    rows: int,
    size: Tuple[int, int],
    output_path: Path,
    image_format: str,
    image_quality: int,
) -> None:
    """
    Stitches frames into a single sprite image.
    """
    width, height = size
    sprite = Image.new("RGB", (cols * width, rows * height))
    for idx, frame in enumerate(sorted(frames)):
        img = Image.open(frame).convert("RGB")
        sprite.paste(img, ((idx % cols) * width, (idx // cols) * height))
    # Save sprite using requested format/quality
    save_image(sprite, output_path, image_format, image_quality)


def write_vtt(timestamps: List[float], cols: int, size: Tuple[int, int], sprite_rel: str, out_vtt: Path) -> None:
    """
    Generates a WebVTT file for the sprite.
    """
    width, height = size
    lines = ["WEBVTT", ""]
    for idx, ts in enumerate(timestamps):
        start = format_timestamp(ts)
        end = format_timestamp(timestamps[idx + 1]) if idx + 1 < len(timestamps) else format_timestamp(ts + 1)
        x, y = (idx % cols) * width, (idx // cols) * height
        lines.append(f"{start} --> {end}")
        lines.append(f"{sprite_rel}#xywh={x},{y},{width},{height}")
        lines.append("")
    out_vtt.write_text("\n".join(lines), encoding="utf-8")


def write_vtt_tiles(
    timestamps: List[float],
    size: Tuple[int, int],
    tiles_dir_rel: str,
    out_vtt: Path,
    image_ext: str,
) -> None:
    """
    Generates a WebVTT file that references individual tile images instead of a sprite.
    """
    lines = ["WEBVTT", ""]
    for idx, ts in enumerate(timestamps):
        start = format_timestamp(ts)
        end = format_timestamp(timestamps[idx + 1]) if idx + 1 < len(timestamps) else format_timestamp(ts + 1)
        tile_name = f"tile_{idx:05d}.{image_ext}"
        lines.append(f"{start} --> {end}")
        lines.append(f"{tiles_dir_rel}/{tile_name}")
        lines.append("")
    out_vtt.write_text("\n".join(lines), encoding="utf-8")


def save_image(img: Image.Image, output_path: Path, image_format: str, quality: int) -> None:
    """
    Save an image to the desired format with reasonable compression settings.
    """
    fmt = image_format.lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "webp":
        img.save(output_path, format="WEBP", quality=quality, method=6)
    elif fmt in ("jpg", "jpeg"):
        img.save(output_path, format="JPEG", quality=quality, optimize=True, progressive=True)
    elif fmt == "png":
        img.save(output_path, format="PNG", optimize=True, compress_level=9)
    else:
        # Fallback to PNG if unknown
        img.save(output_path, format="PNG", optimize=True, compress_level=9)


def process_single_video(
    input_path: Path,
    outdir: Path,
    cols: int,
    rows_opt: int | None,
    width: int,
    height: int,
    interval: int,
    quality: int,
    vtt_mode: str,
    image_format: str,
    image_quality: int,
    hwaccel: str = DEFAULT_HWACCEL,
) -> None:
    tile_w, tile_h = width, height

    duration = probe_duration(input_path)
    timestamps = [max(0.5, i) for i in range(0, int(duration), interval)]
    total_tiles = len(timestamps)
    rows = rows_opt if rows_opt else math.ceil(total_tiles / cols)

    logging.info(f"Duration: {duration:.2f}s | Thumbnails: {total_tiles} ({cols}x{rows})")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        frames = extract_frames_parallel(input_path, timestamps, (tile_w, tile_h), tmpdir, quality, hwaccel, image_format)
        base = input_path.stem
        vtt_path = outdir / f"{base}_sprite.vtt"

        if vtt_mode == "sprite":
            sprite_path = outdir / f"{base}_sprite.{image_format}"
            logging.info("Building sprite image...")
            build_sprite(frames, cols, rows, (tile_w, tile_h), sprite_path, image_format, image_quality)
            sprite_rel = f"{sprite_path.name}"
            write_vtt(timestamps, cols, (tile_w, tile_h), sprite_rel, vtt_path)
        else:
            tiles_dir = outdir / f"{base}_tiles"
            logging.info("Saving tiles images...")
            for idx, frame in enumerate(sorted(frames)):
                img = Image.open(frame).convert("RGB")
                tile_out = tiles_dir / f"tile_{idx:05d}.{image_format}"
                save_image(img, tile_out, image_format, image_quality)
                img.close()
            tiles_dir_rel = f"{base}_tiles"
            write_vtt_tiles(timestamps, (tile_w, tile_h), tiles_dir_rel, vtt_path, image_format)
            sprite_path = tiles_dir

    logging.info(f"Output: {sprite_path}")
    logging.info(f"VTT: {vtt_path}")

    # Save metadata
    metadata_path = outdir / f"{base}_meta.json"
    metadata = {
        "duration": duration,
        "width": width,
        "height": height,
        "sprite": {
            "path": str(sprite_path),
            "vtt": str(vtt_path),
        }
    }
    metadata_path.write_text(str(metadata))
    logging.info(f"Metadata: {metadata_path}")


def main():
    p = argparse.ArgumentParser(description="Generate high-quality thumbnail sprites and WebVTT files.")
    p.add_argument("--input", required=True, help="Path to the input video file or directory.")
    p.add_argument("--outdir", required=True, help="Directory to save the output files.")
    p.add_argument("--cols", type=int, default=DEFAULT_COLS, help="Number of columns in the sprite sheet.")
    p.add_argument("--rows", type=int, help="Number of rows in the sprite sheet (auto if not provided).")
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Width of each thumbnail image.")
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Height of each thumbnail image.")
    p.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="Interval in seconds between each thumbnail.")
    p.add_argument("--quality", type=int, default=DEFAULT_QUALITY, help="FFmpeg/WebP quality (lower is better).")
    p.add_argument("--vtt-mode", choices=["sprite", "tiles"], default=DEFAULT_VTT_MODE, help="Whether to reference a single sprite image or per-tile images in the VTT.")
    p.add_argument("--image-format", choices=["webp", "jpeg", "png"], default=DEFAULT_IMAGE_FORMAT, help="Image format for outputs (sprite or tiles).")
    p.add_argument("--image-quality", type=int, default=DEFAULT_IMAGE_QUALITY, help="Image quality for outputs (WEBP/JPEG). 1-100")
    p.add_argument("--hwaccel", choices=["none", "cuda", "qsv", "d3d11va"], default=DEFAULT_HWACCEL, help="Hardware acceleration for decode, if available.")
    p.add_argument("--mode", choices=["sprite", "thumbnail"], default="sprite", help="Operation mode.")
    p.add_argument("--timestamp", type=float, default=10.0, help="Timestamp for single thumbnail extraction.")
    args = p.parse_args()

    in_arg = Path(args.input)
    outdir = Path(args.outdir)

    try:
        if args.mode == "thumbnail":
            if not in_arg.is_file():
                logging.error("Input must be a file for thumbnail mode.")
                sys.exit(1)

            out_path = outdir / f"{in_arg.stem}.jpeg"
            extract_frame(in_arg, args.timestamp, (args.width, args.height), out_path, args.quality, args.hwaccel, "jpeg")
            logging.info(f"Thumbnail saved to {out_path}")

        elif in_arg.is_dir():
            video_files: List[Path] = []
            for ext in ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.webm"):
                video_files.extend(sorted(in_arg.glob(ext)))
            if not video_files:
                logging.warning(f"No video files found in directory: {in_arg}")
                sys.exit(0)
            for vf in video_files:
                logging.info(f"Processing video: {vf.name}")
                process_single_video(
                    vf,
                    outdir,
                    args.cols,
                    args.rows,
                    args.width,
                    args.height,
                    args.interval,
                    args.quality,
                    args.vtt_mode,
                    args.image_format,
                    args.image_quality,
                    args.hwaccel,
                )
        elif in_arg.is_file():
            process_single_video(
                in_arg,
                outdir,
                args.cols,
                args.rows,
                args.width,
                args.height,
                args.interval,
                args.quality,
                args.vtt_mode,
                args.image_format,
                args.image_quality,
                args.hwaccel,
            )
        else:
            logging.error("Input path not found. Provide --input (file or directory).")
            sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
