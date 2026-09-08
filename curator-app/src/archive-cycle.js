import cycle from "../../config/archive-cycle.json" with { type: "json" };

export function isActiveArchiveIssue(issue) {
  return Number.isInteger(issue?.number) && issue.number > cycle.legacy_issue_ceiling
    && Number.isFinite(Date.parse(issue.created_at))
    && Date.parse(issue.created_at) >= Date.parse(cycle.reset_at);
}
