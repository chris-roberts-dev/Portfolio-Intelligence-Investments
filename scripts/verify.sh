#!/usr/bin/env bash

# Run all project quality checks and report failures together.
#
# Usage:
#   make verify
#   ./scripts/verify.sh

set -u

FAILED=0
FAILED_CHECKS=()

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

run_check() {
    local name="$1"
    shift

    local log_file="$TMP_DIR/${name}.log"

    echo
    echo "============================================================"
    echo "Running: $name"
    echo "============================================================"

    if "$@" >"$log_file" 2>&1; then
        echo "✓ $name passed"
    else
        local exit_code=$?

        echo "✗ $name failed (exit code $exit_code)"

        FAILED=1
        FAILED_CHECKS+=("$name")
    fi
}

run_check "lint" \
    bash -c 'cd backend && uv run ruff check .'

run_check "format-check" \
    bash -c 'cd backend && uv run ruff format --check .'

run_check "typecheck" \
    bash -c 'cd backend && uv run mypy'

run_check "test" \
    docker compose exec -T backend \
    uv run pytest -q --ds=config.settings.test

run_check "openapi" \
    docker compose run --rm backend \
    python manage.py spectacular \
    --validate \
    --file openapi.yaml


echo
echo "============================================================"
echo "Verification Summary"
echo "============================================================"

if [ "$FAILED" -eq 0 ]; then
    echo "✓ All checks passed."
    exit 0
fi

echo "✗ ${#FAILED_CHECKS[@]} check(s) failed:"
echo

for check in "${FAILED_CHECKS[@]}"; do
    echo "------------------------------------------------------------"
    echo "FAILED: $check"
    echo "------------------------------------------------------------"
    cat "$TMP_DIR/${check}.log"
    echo
done

echo "============================================================"
echo "Failed checks:"
printf '  ✗ %s\n' "${FAILED_CHECKS[@]}"
echo "============================================================"

exit 1