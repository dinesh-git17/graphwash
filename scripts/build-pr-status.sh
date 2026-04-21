#!/usr/bin/env bash
# Build the sticky PR status comment body. Reads REPO, PR_NUMBER, HEAD_SHA,
# and GH_TOKEN from the environment; calls `gh api` for workflow runs + jobs
# and `gh pr view` for mergeability; emits `body` via $GITHUB_OUTPUT as a
# multiline variable.

set -euo pipefail

repo="${REPO:?REPO env var required}"
pr_number="${PR_NUMBER:?PR_NUMBER env var required}"
head_sha="${HEAD_SHA:?HEAD_SHA env var required}"
output_file="${GITHUB_OUTPUT:?GITHUB_OUTPUT not set}"

tracked_workflows=(ci pr-label docs-site docker-ci)

glyph_for() {
    local status="$1" conclusion="$2"
    if [[ "$status" != "completed" ]]; then
        printf '[RUN] '
        return
    fi
    case "$conclusion" in
        success)    printf '[PASS]' ;;
        failure)    printf '[FAIL]' ;;
        cancelled)  printf '[CANX]' ;;
        skipped)    printf '[SKIP]' ;;
        neutral|"") printf '[----]' ;;
        *)          printf '[----]' ;;
    esac
}

merge_state_label() {
    case "$1" in
        CLEAN)    printf '[OK]   mergeable' ;;
        UNSTABLE) printf '[WARN] mergeable (non-required checks failing)' ;;
        BLOCKED)  printf '[STOP] blocked' ;;
        BEHIND)   printf '[WAIT] behind main' ;;
        DIRTY)    printf '[CONF] merge conflict' ;;
        *)        printf '[....] computing' ;;
    esac
}

fmt_duration() {
    local started="$1" updated="$2" status="$3"
    if [[ "$status" != "completed" || -z "$started" || -z "$updated" ]]; then
        printf -- '--'
        return
    fi
    local s u delta
    s="$(date -d "$started" +%s)"
    u="$(date -d "$updated" +%s)"
    delta=$((u - s))
    if (( delta < 1 )); then
        delta=1
    fi
    printf '%ds' "$delta"
}

allowlist_json="$(printf '%s\n' "${tracked_workflows[@]}" | jq -Rcs 'split("\n") | map(select(length>0))')"

runs_json="$(
    gh api "/repos/$repo/actions/runs?head_sha=$head_sha&per_page=50" \
    | jq -c --arg sha "$head_sha" --argjson allow "$allowlist_json" '
        .workflow_runs
        | map(select(.head_sha == $sha))
        | map(select(.name as $n | $allow | index($n)))
        | group_by(.name)
        | map(max_by(.id))
    '
)"

rows=""
for name in "${tracked_workflows[@]}"; do
    run="$(printf '%s' "$runs_json" | jq -c --arg n "$name" '.[] | select(.name == $n)')"
    if [[ -z "$run" ]]; then
        continue
    fi
    run_id="$(printf '%s' "$run" | jq -r '.id')"
    if [[ "$name" == "ci" ]]; then
        jobs_json="$(gh api "/repos/$repo/actions/runs/$run_id/jobs" | jq -c '.jobs')"
        while IFS=$'\t' read -r jname jstatus jconclusion jstarted jcompleted; do
            glyph="$(glyph_for "$jstatus" "$jconclusion")"
            dur="$(fmt_duration "$jstarted" "$jcompleted" "$jstatus")"
            label="${jconclusion:-${jstatus//_/ }}"
            rows+="| ci | ${jname} | ${glyph} ${label} | ${dur} |"$'\n'
        done < <(printf '%s' "$jobs_json" | jq -r '.[] | [.name, .status, (.conclusion // ""), .started_at, (.completed_at // "")] | @tsv')
    else
        status="$(printf '%s' "$run" | jq -r '.status')"
        conclusion="$(printf '%s' "$run" | jq -r '.conclusion // ""')"
        started="$(printf '%s' "$run" | jq -r '.run_started_at')"
        updated="$(printf '%s' "$run" | jq -r '.updated_at')"
        glyph="$(glyph_for "$status" "$conclusion")"
        dur="$(fmt_duration "$started" "$updated" "$status")"
        label="${conclusion:-${status//_/ }}"
        rows+="| ${name} | -- | ${glyph} ${label} | ${dur} |"$'\n'
    fi
done

merge_state="$(gh pr view "$pr_number" --json mergeStateStatus --jq '.mergeStateStatus // "UNKNOWN"')"
merge_label="$(merge_state_label "$merge_state")"

updated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
sha_short="${head_sha:0:7}"

body="<!-- graphwash-status -->
## PR status · ${sha_short}

| Workflow | Job  | Status          | Duration |
| -------- | ---- | --------------- | -------- |
${rows}
**Mergeability:** ${merge_label}

_Updated ${updated_at}_
"

{
    printf 'body<<GRAPHWASH_EOF\n'
    printf '%s\n' "$body"
    printf 'GRAPHWASH_EOF\n'
} >> "$output_file"
