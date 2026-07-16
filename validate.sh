#!/usr/bin/env bash
# Lightweight local validation for ollama-stack (no multi-OS shell layouts).
set -euo pipefail
cd "$(dirname "$0")"

echo "Validating ollama-stack..."

fail=0

echo "→ Python syntax: setup.py"
python3 -m py_compile setup.py || fail=1

echo "→ Python syntax: test/*.py"
for f in test/test_*.py; do
  python3 -m py_compile "$f" || fail=1
done

echo "→ Shell syntax: validate.sh + test helpers"
bash -n validate.sh || fail=1
for f in test/*.sh; do
  [ -f "$f" ] || continue
  bash -n "$f" || fail=1
done

if command -v docker >/dev/null 2>&1; then
  echo "→ docker compose config"
  if docker compose version >/dev/null 2>&1; then
    docker compose -f docker-compose.yml config >/dev/null || fail=1
    docker compose -f docker-compose.test.yml config >/dev/null || fail=1
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f docker-compose.yml config >/dev/null || fail=1
    docker-compose -f docker-compose.test.yml config >/dev/null || fail=1
  else
    echo "  (docker present but compose unavailable — skip)"
  fi
else
  echo "→ docker compose config (skipped — docker not installed)"
fi

if [ -d .venv ]; then
  echo "→ unit tests (test_setup.py)"
  .venv/bin/python -m pytest test/test_setup.py -q -p no:cov --override-ini='addopts=' || fail=1
else
  echo "→ unit tests (skipped — no .venv; run: uv venv && uv pip install -r requirements-test.txt)"
fi

if [ "$fail" -ne 0 ]; then
  echo "Validation: FAILED"
  exit 1
fi

echo "Validation: PASSED"
