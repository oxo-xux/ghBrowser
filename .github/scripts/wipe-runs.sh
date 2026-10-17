#!/usr/bin/env bash
# Deletes finished GitHub Actions run history for a repository.
#
# Env:
#   GH_TOKEN   token with actions:write (github.token works when the job has that permission)
#   REPO       owner/name
#   CURRENT_RUN_ID  run id to never touch (the running one); defaults to this job's run
#   KEEP_LATEST     finished runs to keep per workflow, 0 = delete everything (default)
set -uo pipefail

REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
CURRENT_RUN_ID="${CURRENT_RUN_ID:-${GITHUBUB_RUN_ID:-}}"
KEEP_LATEST="${KEEP_LATEST:-0}"

if [ -z "${GH_TOKEN:-}" ] || [ -z "$REPO" ]; then
  echo "wipe-runs: GH_TOKEN and REPO are required, skipping."
  exit 0
fi
if ! [[ "$KEEP_LATEST" =~ ^[0-9]+$ ]]; then KEEP_LATEST=0; fi

echo "wipe-runs: repo=$REPO self=$CURRENT_RUN_ID keep_latest=$KEEP_LATEST"

LIST=$(mktemp)
trap 'rm -f "$LIST"' EXIT

PAGE=1
while :; do
  if ! BODY=$(gh api "repos/$REPO/actions/runs?per_page=100&page=$PAGE" 2>&1); then
    echo "wipe-runs: could not list runs: $BODY"
    exit 0
  fi
  COUNT=$(jq '.workflow_runs | length' <<< "$BODY" 2>/dev/null) || COUNT=0
  jq -r '.workflow_runs[] | [.id, .workflow_id, (.run_number | tostring), .status] | @tsv' <<< "$BODY" >> "$LIST" 2>/dev/null
  [ "$COUNT" -lt 100 ] && break
  PAGE=$((PAGE + 1))
  if [ "$PAGE" -gt 50 ]; then
    echo "wipe-runs: page safety stop reached"
    break
  fi
done

TOTAL=$(grep -c '[0-9]' "$LIST" || true)
echo "wipe-runs: $TOTAL runs found"

if [ "$KEEP_LATEST" -eq 0 ]; then
  DEL=$(awk -F'\t' -v self="$CURRENT_RUN_ID" '$4 == "completed" && $1 != self { print $1 }' "$LIST")
else
  DEL=$(sort -t$'\t' -k2,2n -k3,3nr "$LIST" \
    | awk -F'\t' -v keep="$KEEP_LATEST" -v self="$CURRENT_RUN_ID" '
        $4 != "completed" || $1 == self { next }
        { if (!($2 in n)) n[$2] = 0; n[$2]++; if (n[$2] > keep) print $1 }')
fi

DELETED=0
FAILED=0
while IFS= read -r ID; do
  [ -z "$ID" ] && continue
  if gh api -X DELETE "repos/$REPO/actions/runs/$ID" >/dev/null 2>&1; then
    DELETED=$((DELETED + 1))
    [ $((DELETED % 25)) -eq 0 ] && echo "wipe-runs: ... $DELETED deleted"
  else
    FAILED=$((FAILED + 1))
    echo "wipe-runs: failed to delete run $ID"
  fi
done <<< "$DEL"

echo "wipe-runs: done. scanned=$TOTAL deleted=$DELETED failed=$FAILED"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### Run history wiped"
    echo ""
    echo "- Trigger: ${GITHUB_WORKFLOW:-unknown} / ${GITHUB_EVENT_NAME:-unknown}"
    echo "- Runs scanned: $TOTAL"
    echo "- Runs deleted: $DELETED"
    echo "- Failed: $FAILED"
    echo "- Kept newest per workflow: $KEEP_LATEST"
  } >> "$GITHUB_STEP_SUMMARY"
fi