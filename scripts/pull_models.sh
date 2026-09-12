#!/usr/bin/env bash
# Pulls the open-weight models this project is configured for by default.
# Requires Ollama installed (https://ollama.com) and running.
#
# Match these to whatever you set OLLAMA_TEXT_MODEL / OLLAMA_VISION_MODEL
# to in backend/.env if you change the defaults.
set -e

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama isn't installed. Install it from https://ollama.com then re-run this script."
  exit 1
fi

echo "==> Pulling text model (llama3.1:8b) — this is several GB, be patient"
ollama pull llama3.1:8b

echo "==> Pulling vision model (llava) for the vision agent"
ollama pull llava

echo ""
echo "Done. Set MOCK_LLM=false in backend/.env and restart the backend to use these."
