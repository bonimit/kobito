#!/usr/bin/env bash
# Builds the browser (WASM) version of Kobito with Pygbag and leaves a
# static, deployable site in build/web.
#
# Run this on a machine with normal internet access -- Pygbag downloads
# its Emscripten/CPython-WASM runtime template from pygame-web.github.io
# on first build, which sandboxed CI/agent environments often block.
#
# Usage (from the repository root):
#   pip install pygbag
#   ./packaging/build_web.sh
#
# Then deploy the result to Vercel:
#   npx vercel deploy build/web --prod
#
# (Any static host works the same way -- Netlify, GitHub Pages, S3+CDN,
# etc. -- since build/web is just plain HTML/JS/WASM with no server.)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pygbag --build .
echo
echo "Built. Static site is in build/web -- deploy that folder as-is."
