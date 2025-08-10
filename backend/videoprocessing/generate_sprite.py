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


def extract_frame(input_path: Path, ts: float, size: Tuple[int, int], out: Path, quality: int):
    """
    Extracts a single frame at a specific timestamp.
    """
    width, height = size
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(ts), "-i", str(input_path),
        "-frames:v", "1",
        "-vf", f"scale={width}:{height}:flags=lanczos",  # Higher quality scaling
        "-f", "image2", "-q:v", str(quality),
        str(out),
        "-hide_banner", "-loglevel", "error"
    ], check=True)


def extract_frames_parallel(input_path: Path, timestamps: List[float], size: Tuple[int, int], tmpdir: Path, quality: int) -> List[Path]:
    """
    Extracts frames in parallel using a thread pool.
    """
    start_time = time.time()
    frames = []
    total = len(timestamps)
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {}
        for idx, ts in enumerate(timestamps):
            out = tmpdir / f"frame_{idx:05d}.png"
            futures[executor.submit(extract_frame, input_path, ts, size, out, quality)] = idx
            frames.append(out)
        for i, future in enumerate(as_completed(futures)):
            _ = futures[future]
            elapsed = time.time() - start_time
            sys.stdout.write(f"\rExtracting frames: {i+1}/{total} ({(i+1)/total*100:.1f}%) | {elapsed:.1f}s elapsed")
            sys.stdout.flush()
    total_time = time.time() - start_time
    sys.stdout.write(f"\rExtracting frames: done in {total_time:.1f}s{' ' * 20}\n")
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
        img = Image.open(frame).convert("RGB")  # No resize here to avoid quality loss
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


def main():
    p = argparse.ArgumentParser(description="Generate high-quality thumbnail sprites and WebVTT files.")
    p.add_argument("--input", required=True, help="Path to the input video file.")
    p.add_argument("--outdir", required=True, help="Directory to save the output files.")
    p.add_argument("--cols", type=int, default=10, help="Number of columns in the sprite sheet.")
    p.add_argument("--rows", type=int, help="Number of rows in the sprite sheet (calculated automatically if not provided).")
    p.add_argument("--width", type=int, default=320, help="Width of each thumbnail image.")
    p.add_argument("--height", type=int, default=180, help="Height of each thumbnail image.")
    p.add_argument("--interval", type=int, default=5, help="Interval in seconds between each thumbnail.")
    p.add_argument("--quality", type=int, default=1, help="FFmpeg quality scale (lower is better, 1 is near-lossless).")
    p.add_argument("--vtt-mode", choices=["sprite", "tiles"], default="sprite", help="Whether to reference a single sprite image or per-tile images in the VTT.")
    p.add_argument("--image-format", choices=["webp", "jpg", "png"], default="webp", help="Image format for outputs (sprite or tiles).")
    p.add_argument("--image-quality", type=int, default=100, help="Image quality for outputs (WEBP/JPEG). 1-100")
    args = p.parse_args()

    input_path, outdir = Path(args.input), Path(args.outdir)
    tile_w, tile_h = args.width, args.height

    duration = probe_duration(input_path)
    timestamps = [max(0.5, i) for i in range(0, int(duration), args.interval)]
    total_tiles = len(timestamps)
    rows = args.rows if args.rows else math.ceil(total_tiles / args.cols)

    sys.stdout.write(f"Duration: {duration:.2f}s | Thumbnails: {total_tiles} ({args.cols}x{rows})\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        frames = extract_frames_parallel(input_path, timestamps, (tile_w, tile_h), tmpdir, args.quality)
        base = input_path.stem
        vtt_path = outdir / f"{base}_sprite.vtt"

        if args.vtt_mode == "sprite":
            sprite_path = outdir / f"{base}_sprite.{args.image_format}"
            sys.stdout.write("Building sprite image...\n")
            build_sprite(frames, args.cols, rows, (tile_w, tile_h), sprite_path, args.image_format, args.image_quality)
            sprite_rel = f"{sprite_path.name}"  # Use relative path
            write_vtt(timestamps, args.cols, (tile_w, tile_h), sprite_rel, vtt_path)
        else:
            # Tiles mode: save individual images and reference them from the VTT
            tiles_dir = outdir / f"{base}_tiles"
            sys.stdout.write("Saving tiles images...\n")
            for idx, frame in enumerate(sorted(frames)):
                img = Image.open(frame).convert("RGB")
                tile_out = tiles_dir / f"tile_{idx:05d}.{args.image_format}"
                save_image(img, tile_out, args.image_format, args.image_quality)
                # Free resources promptly
                img.close()
            tiles_dir_rel = f"{base}_tiles"
            write_vtt_tiles(timestamps, (tile_w, tile_h), tiles_dir_rel, vtt_path, args.image_format)
            sprite_path = tiles_dir  # for a unified completion message

    sys.stdout.write(f"Output: {sprite_path}\nVTT: {vtt_path}\n")


if __name__ == "__main__":
    main()
