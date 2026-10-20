#!/usr/bin/env bash
# Builds the browser (WASM) version of Kobito with Pygbag and leaves a
# static, deployable site in build/web (index.html + kobito.apk).
#
# Only what the game needs goes in -- main.py, kobito/ and assets/ -- so
# the download players wait for doesn't carry the docs' videos, tools or
# the leaderboard server.
#
# Pygbag downloads its CPython-WASM runtime template from
# pygame-web.github.io, so run this somewhere with normal internet access:
# GitHub Actions does it on every push (.github/workflows/web.yml).
#
# Usage (from the repository root):
#   pip install pygbag
#   ./packaging/build_web.sh
#   python -m http.server -d build/web 8000     # then open http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/.."
STAGE=build/web-src/kobito
rm -rf build/web-src build/web
mkdir -p "$STAGE"
cp -r main.py kobito assets "$STAGE/"
find "$STAGE" -name __pycache__ -type d -prune -exec rm -rf {} +
python3 -m pygbag --title "Kobito" --build "$STAGE"
cp -r "$STAGE/build/web" build/web
echo
echo "Built. Static site is in build/web -- deploy that folder as-is."
