#!/usr/bin/env bash
# Sync GitHub labels from .github/labels.yml. Idempotent: create if missing,
# edit if present. Requires gh and yq (mikefarah v4).

set -euo pipefail

LABELS_FILE=".github/labels.yml"

command -v gh >/dev/null 2>&1 || { echo "error: gh CLI required" >&2; exit 1; }
command -v yq >/dev/null 2>&1 || { echo "error: yq (mikefarah v4) required" >&2; exit 1; }

if [[ ! -f "$LABELS_FILE" ]]; then
    echo "error: $LABELS_FILE not found" >&2
    exit 1
fi

count="$(yq 'length' "$LABELS_FILE")"
if [[ "$count" -eq 0 ]]; then
    echo "error: no labels defined in $LABELS_FILE" >&2
    exit 1
fi

echo "syncing $count labels to $(gh repo view --json nameWithOwner -q .nameWithOwner)"

created=0
updated=0
failed=0

for i in $(seq 0 $((count - 1))); do
    name="$(yq -r ".[$i].name" "$LABELS_FILE")"
    color="$(yq -r ".[$i].color" "$LABELS_FILE")"
    description="$(yq -r ".[$i].description" "$LABELS_FILE")"

    if gh label create "$name" --color "$color" --description "$description" 2>/dev/null; then
        echo "created: $name"
        created=$((created + 1))
    elif gh label edit "$name" --color "$color" --description "$description" >/dev/null; then
        echo "updated: $name"
        updated=$((updated + 1))
    else
        echo "failed:  $name" >&2
        failed=$((failed + 1))
    fi
done

echo
echo "summary: created=$created updated=$updated failed=$failed"

if [[ "$failed" -gt 0 ]]; then
    exit 1
fi
