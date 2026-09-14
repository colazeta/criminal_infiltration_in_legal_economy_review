#!/usr/bin/env bash
# Called only after the full mandatory validation. No direct-main fallback.
set -euo pipefail
: "${GITHUB_REPOSITORY:?}" "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
base_sha="$(git rev-parse HEAD)"
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
# Stable checkpoint identity: an identical validated mechanical diff from the same
# main base must reuse the retained branch/PR rather than multiplying run-id branches.
diff_digest="$( { printf '%s\n' "$base_sha"; git diff --binary -- "${paths[@]}"; } | sha256sum | cut -c1-20 )"
branch="automation/selected-support-${diff_digest}"
pr_url=""
head_sha=""
pending() {
  echo "::error::Support persistence is pending: $1"
  {
    echo "## Recoverable selected-support checkpoint"
    echo "Status: persistence_pending; not published and not scientifically approved."
    echo "Branch: $branch"
    echo "Head: ${head_sha:-not-yet-persisted}"
    echo "Validated base: $base_sha"
    echo "PR: ${pr_url:-creation blocked}"
    echo "Blocker: $1"
    echo "Next: reuse this branch, reconcile current main, run full mandatory validation and merge only with a successful quality check."
  } >> "$GITHUB_STEP_SUMMARY"
  exit 1
}

# Build the exact tree that the already-validated working copy would persist,
# without mutating the real index. A reused remote branch must match this tree and
# descend from the validated base before it can be trusted or auto-merged.
checkpoint_index="$RUNNER_TEMP/selected-support-index"
rm -f "$checkpoint_index"
GIT_INDEX_FILE="$checkpoint_index" git read-tree "$base_sha" || pending "checkpoint_expected_tree_failed"
GIT_INDEX_FILE="$checkpoint_index" git add -A -- "${paths[@]}" || pending "checkpoint_expected_tree_failed"
expected_tree="$(GIT_INDEX_FILE="$checkpoint_index" git write-tree)" || pending "checkpoint_expected_tree_failed"
rm -f "$checkpoint_index"

write_pr_body() {
  cat > "$RUNNER_TEMP/selected-support-pr.md" <<EOF
Mechanical retrieval/abstract-support and deterministic public projections only.

Full AGENTS.md mandatory validation completed before this branch was committed.
No new CandidateRecord, eligibility decision, canonical merge, private evidence or
scientific classification is included. Review and a successful ordinary quality
check remain required before merge. No direct-main fallback is permitted.

Base: $base_sha
Head: $head_sha
Source run: $GITHUB_RUN_ID
Checkpoint digest: $diff_digest
EOF
}

create_checkpoint_pr() {
  write_pr_body
  local created=""
  if created="$(gh pr create --base main --head "$branch" --title "Refresh validated reading-support projections" --body-file "$RUNNER_TEMP/selected-support-pr.md")"; then
    pr_url="$created"
  else
    # PR creation can fail after the server accepted the mutation. Read back the
    # exact head before declaring the checkpoint blocked or attempting anything else.
    pr_url="$(gh pr list --state open --base main --head "$branch" --json url,headRefOid --jq '.[0] | select(.headRefOid == "'"$head_sha"'") | .url')" || true
    [ -n "$pr_url" ] || pending "pr_creation_blocked"
  fi
  [ -n "$pr_url" ] || pending "pr_creation_blocked"
}

verify_remote_checkpoint() {
  git fetch --no-tags origin "$branch" || pending "checkpoint_fetch_failed"
  head_sha="$(git rev-parse FETCH_HEAD)" || pending "checkpoint_readback_incomplete"
  local merge_base remote_tree
  merge_base="$(git merge-base "$base_sha" "$head_sha")" || pending "checkpoint_base_mismatch"
  [ "$merge_base" = "$base_sha" ] || pending "checkpoint_base_mismatch"
  remote_tree="$(git rev-parse "$head_sha^{tree}")" || pending "checkpoint_readback_incomplete"
  [ "$remote_tree" = "$expected_tree" ] || pending "checkpoint_head_mismatch"
}

if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
  verify_remote_checkpoint
  checkpoint="$(gh pr list --state open --base main --head "$branch" --json url,headRefOid --jq '.[0] | [.url, .headRefOid] | @tsv')" || pending "checkpoint_lookup_failed"
  if [ -n "$checkpoint" ]; then
    pr_head_sha=""
    IFS=$'\t' read -r pr_url pr_head_sha <<< "$checkpoint"
    [ -n "$pr_url" ] && [ -n "$pr_head_sha" ] || pending "checkpoint_readback_incomplete"
    [ "$pr_head_sha" = "$head_sha" ] || pending "checkpoint_pr_head_mismatch"
    echo "Reusing retained selected-support checkpoint: $pr_url" >> "$GITHUB_STEP_SUMMARY"
  else
    # Recover a branch that was successfully pushed before PR creation failed.
    create_checkpoint_pr
    checkpoint="$(gh pr list --state open --base main --head "$branch" --json url,headRefOid --jq '.[0] | [.url, .headRefOid] | @tsv')" || pending "checkpoint_lookup_failed"
    [ -n "$checkpoint" ] || pending "checkpoint_pr_readback_missing"
    pr_head_sha=""
    IFS=$'\t' read -r pr_url pr_head_sha <<< "$checkpoint"
    [ -n "$pr_url" ] && [ "$pr_head_sha" = "$head_sha" ] || pending "checkpoint_pr_head_mismatch"
    echo "Recovered selected-support PR for retained validated branch: $pr_url" >> "$GITHUB_STEP_SUMMARY"
  fi
else
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git checkout -b "$branch"
  git add -- "${paths[@]}"
  git commit -m "Refresh validated reading-support projections"
  git push origin "$branch" || pending "checkpoint_push_failed"
  head_sha="$(git rev-parse HEAD)"
  [ "$(git rev-parse "$head_sha^{tree}")" = "$expected_tree" ] || pending "checkpoint_head_mismatch"
  create_checkpoint_pr
fi

# PRs created with the repository GITHUB_TOKEN do not recursively trigger a PR
# workflow. workflow_dispatch is the supported exception. Evaluate only the most
# recent exact-head quality check: historical failures/action_required outcomes
# remain audit evidence but must not permanently poison a reusable checkpoint.
latest_quality_state() {
  gh api "repos/$GITHUB_REPOSITORY/commits/$head_sha/check-runs" --jq '
    [.check_runs[] | select(.name == "quality" and .app.slug == "github-actions")]
    | sort_by(.started_at // .created_at // "")
    | if length == 0 then "missing"
      else last
      | if (.status == "in_progress" or .status == "queued") then "pending"
        elif .conclusion == "success" then "success"
        elif (.conclusion == "failure" or .conclusion == "action_required" or .conclusion == "cancelled") then "blocked"
        else "pending"
        end
      end'
}
quality_state="$(latest_quality_state)" || pending "quality_read_failed"
if [ "$quality_state" = "missing" ] || [ "$quality_state" = "blocked" ]; then
  gh workflow run archive.yml --ref "$branch" || pending "quality_dispatch_failed"
  echo "Dispatched replacement exact-head quality validation for retained checkpoint." >> "$GITHUB_STEP_SUMMARY"
fi

quality="pending"
for attempt in $(seq 1 18); do
  quality="$(latest_quality_state)" || pending "quality_read_failed"
  [ "$quality" = "success" ] && break
  # A blocked state after dispatch is terminal for this invocation, but the branch
  # and PR remain the recoverable checkpoint for a later exact-head redispatch.
  [ "$quality" = "blocked" ] && pending "quality_blocked"
  [ "$attempt" = 18 ] || sleep 10
done
[ "$quality" = "success" ] || pending "quality_not_successful"
current_main="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main" --jq .object.sha)" || pending "main_read_failed"
[ "$current_main" = "$base_sha" ] || pending "main_moved_reconciliation_required"
pr_number="${pr_url##*/}"
[[ "$pr_number" =~ ^[0-9]+$ ]] || pending "invalid_pr_number"
merged="$(gh api --method PUT "repos/$GITHUB_REPOSITORY/pulls/$pr_number/merge" -f sha="$head_sha" -f merge_method=merge --jq .merged)" || pending "merge_blocked"
[ "$merged" = "true" ] || pending "merge_not_confirmed"
echo "Validated support projections merged through $pr_url. Publication remains a separate observed stage." >> "$GITHUB_STEP_SUMMARY"
