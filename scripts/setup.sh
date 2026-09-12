#!/usr/bin/env bash
# Sets up the backend virtualenv + .env and reminds you what's next.
# Run from the project root: ./scripts/setup.sh
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
  echo "==> Creating Python virtual environment (backend/.venv)"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate

echo "==> Installing backend dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if [ ! -f ".env" ]; then
  echo "==> Creating backend/.env from .env.example"
  cp .env.example .env
fi

mkdir -p data/uploads

echo ""
echo "Backend is ready. Next steps:"
echo "  1. cd backend && . .venv/bin/activate && uvicorn app.main:app --reload"
echo "     (starts in MOCK_LLM mode by default — no GPU or model download needed yet)"
echo "  2. In another terminal: cd frontend && npm install && npm run dev"
echo "  3. Open http://localhost:5173 — admin credentials are printed in the"
echo "     backend's startup log the first time it runs."
echo ""
echo "When you're ready for real, grounded answers instead of mock ones:"
echo "  ./scripts/pull_models.sh"
echo "  then set MOCK_LLM=false in backend/.env and restart uvicorn."
