#!/usr/bin/env bash
# Called only after the full mandatory validation. No direct-main fallback.
set -euo pipefail
: "${GITHUB_REPOSITORY:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
base_sha="$(git rev-parse HEAD)"
branch="automation/selected-support-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:-1}"
paths=(data/curation/retrieval_coverage.csv data/curation/abstract_coverage.csv site/data)
if git diff --quiet -- "${paths[@]}"; then
  echo "Support projections already current; no repository write required." >> "$GITHUB_STEP_SUMMARY"
  exit 0
fi
# Never package a workflow, scientific decision or unrelated concurrent change.
while IFS= read -r path; do
  case "$path" in
    data/curation/retrieval_coverage.csv|data/curation/abstract_coverage.csv|site/data/*) ;;
    *) echo "::error::Unexpected changed path in mechanical support update: $path"; exit 1 ;;
  esac
done < <(git diff --name-only)
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git checkout -b "$branch"
git add -- "${paths[@]}"
git commit -m "Refresh validated reading-support projections"
git push origin "$branch"
head_sha="$(git rev-parse HEAD)"
pr_url=""
pending() {
  echo "::error::Support persistence is pending: $1"
  {
    echo "## Recoverable selected-support checkpoint"
    echo "Status: persistence_pending; not published and not scientifically approved."
    echo "Branch: $branch"
    echo "Head: $head_sha"
    echo "Validated base: $base_sha"
    echo "PR: ${pr_url:-creation blocked}"
    echo "Blocker: $1"
    echo "Next: reuse this branch, reconcile current main, run full mandatory validation and merge only with a successful quality check."
  } >> "$GITHUB_STEP_SUMMARY"
  exit 1
}
cat > "$RUNNER_TEMP/selected-support-pr.md" <<EOF
Mechanical retrieval/abstract-support and deterministic public projections only.

Full AGENTS.md mandatory validation completed before this branch was committed.
No new CandidateRecord, eligibility decision, canonical merge, private evidence or
scientific classification is included. Review and a successful ordinary quality
check remain required before merge. No direct-main fallback is permitted.

Base: $base_sha
Head: $head_sha
Source run: $GITHUB_RUN_ID
EOF
pr_url="$(gh pr create --base main --head "$branch" --title "Refresh validated reading-support projections" --body-file "$RUNNER_TEMP/selected-support-pr.md")" || pending "pr_creation_blocked"
# A GITHUB_TOKEN-created PR may have no runnable checks. Never call that success.
quality="pending"
for attempt in 1 2 3 4 5 6; do
  quality="$(gh api "repos/$GITHUB_REPOSITORY/commits/$head_sha/check-runs" --jq '[.check_runs[] | select(.name == "quality" and .app.slug == "github-actions") | .conclusion] | if length == 0 then "pending" elif all(. == "success") then "success" elif any(. == "failure" or . == "action_required" or . == "cancelled") then "blocked" else "pending" end')" || pending "quality_read_failed"
  [ "$quality" = "success" ] && break
  [ "$quality" = "blocked" ] && pending "quality_blocked"
  [ "$attempt" = 6 ] || sleep 5
done
[ "$quality" = "success" ] || pending "quality_not_successful"
current_main="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main" --jq .object.sha)" || pending "main_read_failed"
[ "$current_main" = "$base_sha" ] || pending "main_moved_reconciliation_required"
pr_number="${pr_url##*/}"
[[ "$pr_number" =~ ^[0-9]+$ ]] || pending "invalid_pr_number"
merged="$(gh api --method PUT "repos/$GITHUB_REPOSITORY/pulls/$pr_number/merge" -f sha="$head_sha" -f merge_method=merge --jq .merged)" || pending "merge_blocked"
[ "$merged" = "true" ] || pending "merge_not_confirmed"
echo "Validated support projections merged through $pr_url. Publication remains a separate observed stage." >> "$GITHUB_STEP_SUMMARY"
