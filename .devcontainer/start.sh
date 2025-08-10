#!/bin/bash

# Make sure mount folder exists in home
mkdir -p ~/filen

# Mount Filen if not already mounted
if ! mountpoint -q ~/filen; then
    echo "Mounting Filen..."
    filen mount ~/filen
fi

# Remove existing folder if it's not a symlink
if [ -d /workspaces/nextjs-video/filen ] && [ ! -L /workspaces/nextjs-video/filen ]; then
    rm -rf /workspaces/nextjs-video/filen
fi

# Create symlink if missing
if [ ! -L /workspaces/nextjs-video/filen ]; then
    ln -s ~/filen /workspaces/nextjs-video/filen
fi
