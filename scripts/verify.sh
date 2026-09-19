#!/usr/bin/env bash

# Run deterministic repository quality checks and report failures together.
# Browser tests remain a separate `make e2e` gate because they start their own
# deterministic demo servers and Chromium process.

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

run_check "backend-lint" \
    bash -c 'cd backend && uv run ruff check .'

run_check "backend-format-check" \
    bash -c 'cd backend && uv run ruff format --check .'

run_check "backend-typecheck" \
    bash -c 'cd backend && uv run mypy'

run_check "django-check" \
    docker compose run --rm backend python manage.py check

run_check "migration-drift" \
    docker compose run --rm backend python manage.py makemigrations --check --dry-run

run_check "migrate-check" \
    docker compose run --rm backend python manage.py migrate --check

run_check "backend-test" \
    docker compose run --rm backend uv run pytest -q --ds=config.settings.test

run_check "frontend-typecheck" \
    bash -c 'cd frontend && npm run typecheck'

run_check "frontend-test" \
    bash -c 'cd frontend && npm test'

run_check "frontend-build" \
    bash -c 'cd frontend && npm run build'

run_check "openapi-drift" \
    docker compose run --rm backend sh -lc \
    'python manage.py spectacular --fail-on-warn --validate --file openapi.generated.yaml && diff -u openapi.yaml openapi.generated.yaml; status=$?; rm -f openapi.generated.yaml; exit $status'

echo
echo "============================================================"
echo "Verification Summary"
echo "============================================================"

if [ "$FAILED" -eq 0 ]; then
    echo "✓ All deterministic checks passed."
    echo "Run 'make e2e' separately for the browser gate."
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
