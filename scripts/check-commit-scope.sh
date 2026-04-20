#!/usr/bin/env bash
# Enforce commit subject pattern: type(t-NNN|training): description
# Invoked by the `repo: local` `enforce-scope` hook at commit-msg stage.

set -euo pipefail

msg_file="${1:?commit message file path required}"
pattern='^(feat|fix|chore|docs|refactor|test|infra|ops|spike)\((t-[0-9]{3}|training)\)!?: .+'

subject="$(head -n1 "$msg_file")"

# Allow merge commits and fixup/squash markers to pass unchanged.
case "$subject" in
    "Merge "* | "fixup! "* | "squash! "* | "amend! "* )
        exit 0
        ;;
esac

if ! printf '%s\n' "$subject" | grep -qE "$pattern"; then
    {
        printf 'commit subject does not match required pattern:\n'
        printf '  %s\n\n' "$subject"
        printf 'required:\n'
        printf '  type(scope): description\n\n'
        printf 'accepted types: feat, fix, chore, docs, refactor, test, infra, ops, spike\n'
        printf 'accepted scopes: t-NNN (e.g. t-007) or training\n'
        printf 'examples:\n'
        printf '  infra(t-007): wire pre-commit hooks\n'
        printf '  chore(training): run lucid-sweep-42\n'
    } >&2
    exit 1
fi

exit 0
