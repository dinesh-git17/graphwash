#!/usr/bin/env bash
# Resolve PR number and head SHA from either a pull_request or workflow_run
# event payload. Emits `number` and `sha` via $GITHUB_OUTPUT so downstream
# steps can gate on a non-empty number.

set -euo pipefail

event_path="${GITHUB_EVENT_PATH:?GITHUB_EVENT_PATH not set}"
event_name="${GITHUB_EVENT_NAME:?GITHUB_EVENT_NAME not set}"
output_file="${GITHUB_OUTPUT:?GITHUB_OUTPUT not set}"

number=""
sha=""

case "$event_name" in
    pull_request)
        number="$(jq -r '.pull_request.number // ""' "$event_path")"
        sha="$(jq -r '.pull_request.head.sha // ""' "$event_path")"
        ;;
    workflow_run)
        sha="$(jq -r '.workflow_run.head_sha // ""' "$event_path")"
        number="$(jq -r '.workflow_run.pull_requests[0].number // ""' "$event_path")"
        if [[ -z "$number" && -n "$sha" ]]; then
            number="$(gh pr list --search "$sha" --state open --json number --jq '.[0].number // ""' 2>/dev/null || true)"
        fi
        ;;
    *)
        echo "error: unsupported event $event_name" >&2
        exit 1
        ;;
esac

{
    printf 'number=%s\n' "$number"
    printf 'sha=%s\n' "$sha"
} >> "$output_file"
