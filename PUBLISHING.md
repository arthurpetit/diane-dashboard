# Diane publishing v4 — per-axis pull requests

This contract implements Arthur's 27 September 2026 instruction: each of the five research routines publishes its own substantive iteration through a temporary branch, commit, pull request, verified merge and branch deletion. It supersedes the v3 producer-only/single-writer procedure. It does not change the dashboard schema, `index.html`, its ten general filters, workflows, repository protections, credentials, schedules, or research scope.

## Canonical data and ownership

`main/data.js`, assigning `window.DIANE_OPPORTUNITIES`, remains the only published opportunity dataset. No Google Sheet is a publication source.

Each axis owns only its researched delta and its existing automation checkpoint. A routine must not overwrite another axis's records or checkpoint. The historical `Publication unique Diane` checkpoint remains useful for recovery and validation evidence, but it is no longer an exclusive writer or a prerequisite for acknowledging a verified per-axis merge. Its empty review queue is not evidence that the researchers have no pending work.

The existing outbox protocol stays `diane-publish-v3`; v4 changes the Git workflow, not the schema. Preserve every unacknowledged proposal, source, hash, research lead, error, superseded revision and legacy reference. A pointer to a frozen payload is not the payload itself: retrieve and verify the original, or keep that item `INPUT_PENDING`; never invent missing bytes or mark them recovered. Missing unrelated legacy inputs do not prevent an independently complete, valid, unrestricted delta from being processed. Known relevant restrictions and identity conflicts must still be considered.

## Per-iteration workflow

1. Read the routine's live checkpoint, existing Git attempt/cleanup state and relevant historical receipts. Reconcile earlier ambiguous outcomes before new mutations. Read complete current `main/data.js` with its blob SHA and current main commit. Partial reads must share the same blob. Prioritize pending work before new discoveries.
2. Verify official sources and classify the intended changes. Preserve unknowns explicitly. Select only this axis's independently complete changes. No substantive delta means no empty commit or PR. Incomplete or conflicting records stay pending; do not replace missing records with placeholders.
3. Discover the native GitHub actions actually available in this run. Create a unique temporary branch `diane/axis<N>/<UTC-run-id>` from the verified current main commit. Never reuse another iteration's branch. Record the branch, base and intended proposal IDs durably before risking loss of an in-flight attempt.
4. Validate the exact delta with the existing offline merger and tests. Preserve all unrelated source spans and fields. Review mode deliberately returns unchanged data: a successful review, especially with zero items, is NOT publication and is NOT a changed candidate. Use candidate generation only for an actually authorized, unrestricted batch as described below. Do not change the merger's safety or validation checks to make a rejected item pass.
5. Commit the complete validated candidate to `data.js` on the temporary branch using native `GitHub.update_file`: repository, path, branch, current branch file **blob** SHA, full UTF-8 content and commit message. The wrapper handles base64. No commit SHA, local path, URI or partial patch may stand in for file content/blob SHA. Never write `data.js` directly to main.
6. Open a PR targeting `main`. Verify the changed files and exact diff: only the intended data changes, with no unrelated formatting, UI, workflow or permission edits. Read the actual PR head and base. If main advances or a conflict exists, reconcile/rebuild only this axis delta on the latest main, rerun validation, and recheck the PR. Never force an overwrite of other contributions. Respect required reviews/checks and repository protections. Merge with the expected PR head SHA. A clean Git merge alone does not establish semantic data compatibility.
7. After merge, read the merged/current main data and verify the intended fields and identities, uniqueness and preservation of unrelated work. Only then record a durable receipt with proposal ID, payload hash, PR number, head SHA, merge SHA and data blob SHA, status `INTEGRATED_MAIN`. A branch, commit, open PR, scheduled auto-merge or local test is not an integration receipt. Do not replay an already integrated proposal against a later owner edit.
8. Delete the exact temporary branch after the merge and readback are verified and the receipt is durable. First verify that its head has not acquired unrelated/new work. Confirm deletion. If native branch deletion is unavailable or fails, retain `CLEANUP_PENDING` with repository, branch, PR and verified head/merge SHAs. Retry only the cleanup when legitimately available; never undo or replay the successful data integration. Do not claim deletion or a fully completed workflow without evidence. A branch name alone is not proof that it is safe to delete.
9. Verify the Pages run associated with the merged commit separately (`DEPLOYED_PAGES`), and the served data when accessible (`LIVE_VERIFIED`). A failed HTTP check is not proof the website is broken. Do not rewrite identical data to force deployment. Keep pending deployment/cleanup separate from pending research/integration.

## Errors, permissions and historical blocks

Record actual errors and their demonstrated scope. An old diagnostic that a writer was absent must not replace current native-tool discovery. A historical `BLOCKED_SAFETY` label without its underlying diagnostic is not proof of a blanket restriction on every new proposal; equally, changing branch, tool, agent, payload size or time does not resolve a real applicable denial. Preserve historical records and do not silently reset their states. Do not disguise or replay a genuinely denied change through a new ID, PR, endpoint or account.

Known restricted proposals remain held until legitimate applicable resolution is verified. An unrelated, complete proposal may be processed only when no known restriction applies to it; do not import the obsolete publisher's initial global HOLD as an automatic rule for every axis. If a restriction's scope is genuinely uncertain and may cover the intended operation, retain that operation for clarification rather than inventing permission or a global prohibition.

For an authorized batch, the merger's `publicationGate: AUTHORIZED` and `authorizationEvidence` describe that batch's checked authorization and scope, not the resolution of every historical block. Retain the union of known relevant quarantines. Evidence text must point to real checked authorization; arbitrary strings or synthetic test fixtures are not proof. The offline merger never writes to GitHub and does not itself establish connector permission.

For timeouts/ambiguous responses, inspect branch/PR/main before retrying. For conflicts, reread and reconcile; for 429, honor Retry-After; for transient transport/5xx, use bounded backoff and retain the attempt for later recovery. A real safety/authentication/approval denial stops the relevant mutation; do not retry it as a transient failure or route around it. Never invent a request ID, HTTP status or cause.

## Outbox and validation schema (unchanged)

Keep exactly one JSON block between `DIANE_OUTBOX_V3_BEGIN` and `DIANE_OUTBOX_V3_END` in each routine's existing prompt. Its `protocol` is `diane-publish-v3`, `axis` is 1–5, and it retains `items`, `quarantine`, `researchLeads`, `acknowledged` and existing recovery fields. Do not delete legacy/frozen content during workflow changes.

A ready insert has `id`, integer `axis`, `state: READY`, `op: insert`, `key: {name, url}`, `edition`, `baseBlobSha`, complete `record` and `evidence`. IDs match `[A-Za-z0-9._:-]{1,160}`. Every evidence entry needs an official HTTPS `url`, actual `checkedAt`, and nonempty `supports` listing verified fields. Evidence mentioned only in prose does not fix missing structured fields. An immutable payload correction gets a new ID and explicit `supersedes`, while retaining the earlier version.

Required record text fields: `name`, `url`, `priority`, `type`, `location`, `deadline`, `value`, `fee`, `simplicity`, `career`, `eligibility`, `maxWorks`, `lifetime`, `action`, `verified`. `discipline` and `tags` are nonempty string arrays. Priorities are A1/A2/B/C/Écarté. Extra factual fields remain supported. Unknown facts stay explicit; do not infer student eligibility or selection rates without evidence.

A patch has `op: patch`, `changes` mapping fields to `{beforePresent: true, before: OLD, after: NEW}` or `{beforePresent: false, after: NEW}`, plus additive `addTags`. No automatic deletion or identity/tag replacement. Recheck preconditions against the latest data. Name/URL ambiguity needs reconciliation, not a duplicate insert. Structural validity does not prove source truth or eligibility.

Run actual local tests and review the exact selected queue:

```sh
python -m unittest discover -s tests -v
python tools/merge_opportunities.py \
  --data data.js --queue /tmp/diane-queue.json \
  --expected-blob CURRENT_BLOB_SHA \
  --output /tmp/diane-review.js --report /tmp/diane-review.json \
  --mode review
```

After checking the batch's authorization, use `--mode authorized` with distinct output/report paths to generate a changed candidate. Require no validation errors, round-trip correctness, expected changes only and neighbor preservation. Do not execute arbitrary JavaScript with eval. Local copies/artifacts must hash-match the relevant Git blobs. An old test report cannot be presented as a newly executed test.

## Persistence and reporting

Use the existing task's native update action only; do not create helper automations. Read its live prompt immediately before saving, preserve these current publication instructions and merge concurrent checkpoint progress. Never replace a newer checkpoint from stale memory. Failed saves are not durable receipts. Automation checkpoints are neither infinite queues nor atomic distributed locks; preserve work and state actual capacity/concurrency limitations rather than silently discarding data.

A matching verified receipt and canonical reconciliation are required before moving an item from pending to acknowledged. Retain recovery evidence; do not lose payloads merely because a branch or PR exists. Report exact progress: researched, committed, PR opened, merged, deployed, live verified, branch deleted or cleanup pending. Notify useful changes or concrete new blockers, not repetitive empty reviews or fictitious publication success.
