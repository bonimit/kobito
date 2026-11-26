#!/bin/sh
# Turn docs/trailer_16x9.mp4 into docs/trailer.gif (640 px wide, 12 fps, no sound).
#   sh tools/trailer_gif.sh [width] [fps]
# Pixel art keeps its crisp edges (nearest-neighbour scaling) and the palette is
# tuned per scene. 640 px / 12 fps is about 9 MB for the full minute; trim with
# ffmpeg's -ss / -t if you need it under a site's limit (itch.io covers: 3 MB).
set -e
cd "$(dirname "$0")/.."
W="${1:-640}"
FPS="${2:-12}"
ffmpeg -loglevel error -y -i docs/trailer_16x9.mp4 \
  -vf "fps=$FPS,scale=$W:-1:flags=neighbor,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" \
  -loop 0 docs/trailer.gif
ls -la docs/trailer.gif
