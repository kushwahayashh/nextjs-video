#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import sys

def generate_sprites_for_all_videos(videos_dir, output_dir, interval=5, width=160, height=90):
    """Generate sprite thumbnails for all videos in a directory"""
    
    videos_dir = Path(videos_dir)
    output_dir = Path(output_dir)
    
    if not videos_dir.exists():
        print(f"Videos directory not found: {videos_dir}")
        return
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all video files
    video_extensions = {'.mp4', '.webm', '.ogg', '.ogv', '.avi', '.mov', '.mkv'}
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(videos_dir.glob(f"*{ext}"))
    
    if not video_files:
        print("No video files found in the specified directory")
        return
    
    print(f"Found {len(video_files)} video files")
    
    for video_file in video_files:
        print(f"\nProcessing: {video_file.name}")
        
        cmd = [
            sys.executable, "videoprocessing/generate_sprite.py",
            "--input", str(video_file),
            "--outdir", str(output_dir),
            "--interval", str(interval),
            "--width", str(width),
            "--height", str(height),
            "--image-format", "webp",
            "--image-quality", "80"
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✓ Successfully processed: {video_file.name}")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to process {video_file.name}: {e}")
            print(f"Error output: {e.stderr}")

if __name__ == "__main__":
    # Configuration - adjust these paths as needed
    VIDEOS_DIRECTORY = "../frontend/public/videos"  # or your actual videos directory
    OUTPUT_DIRECTORY = "../frontend/public/processed"  # or your actual output directory
    
    generate_sprites_for_all_videos(VIDEOS_DIRECTORY, OUTPUT_DIRECTORY)