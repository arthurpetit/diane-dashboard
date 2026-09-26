# Diane publishing v3

## Roles and unchanged canonical source

`main/data.js` remains the only published opportunity dataset. The website continues to read `window.DIANE_OPPORTUNITIES`. This redesign does not change `index.html`, the Pages workflow, permissions, hosting, or credentials.

The five research automations are producers only. They read the current dataset and verify public primary sources, but never mutate GitHub. Each saves proposed changes in a structured outbox inside its own existing automation prompt using the native automations update action. This is unpublished work, not another public dataset. One separate publisher automation is the only scheduled writer of `data.js`. It reads the five outboxes, checks evidence and prepares an exact merge using `tools/merge_opportunities.py`.

Outbox persistence is provided by automation checkpoints. It is not a transactional message broker or an infinite-capacity queue. Do not claim exactly-once delivery or a distributed lock. Each producer owns its own outbox; the publisher owns its receipt ledger and does not edit producers. Retain unacknowledged proposals and every unresolved block. Report capacity/access limitations rather than silently discarding work. Preserve enabled/disabled choices and existing research schedules.

## Safety boundary

The initial publisher gate is `HOLD_UNRESOLVED_SAFETY`. It can read, validate and reconcile, but cannot attempt data publication while this gate is held. Previously denied proposals remain quarantined across renames, IDs, runs and tools. Changing the pipeline does not clear a denial. A future new proposal is not allowed to disguise the same refused change.

Reopening requires independently checked evidence of a legitimate resolution of the relevant restriction, such as the applicable native approval process or a service-side resolution. An arbitrary `authorizationEvidence` string is not proof; the publisher must check the actual evidence before using authorized mode. A settings change, another hour, a different agent, a shorter payload or a successful unrelated source-code write is not resolution. Follow the scope of any global restriction. Do not route denied operations through another endpoint, account, token, issue, PR, workflow, server or publisher.

The merger is offline and has no network, credentials, GitHub writes or deployment. Its test fixtures use synthetic authorization solely to test local transformations. Source-code installation or a green test does not establish that the native data write has become authorized.

## Producer outbox

Keep exactly one JSON block between `DIANE_OUTBOX_V3_BEGIN` and `DIANE_OUTBOX_V3_END` in each producer's saved prompt:

```json
{
  "protocol": "diane-publish-v3",
  "axis": 1,
  "items": [],
  "quarantine": [],
  "researchLeads": [],
  "acknowledged": []
}
```

A ready insert has `id`, integer `axis`, `state: READY`, `op: insert`, `key: {name, url}`, `edition`, `baseBlobSha`, `record` and `evidence`. Its complete record follows the existing dashboard fields. Evidence entries contain an official `url`, actual `checkedAt`, and `supports` listing verified fields; do not invent verification timestamps. Unknown facts remain explicit. An ID can be a readable stable axis/slug/revision string; the merger computes its operation hash. Once offered, content is immutable under that ID. A correction gets a new ID and an explicit superseded-ID relationship, without erasing block history.

Record required text fields are `name`, `url`, `priority`, `type`, `location`, `deadline`, `value`, `fee`, `simplicity`, `career`, `eligibility`, `maxWorks`, `lifetime`, `action`, `verified`. `discipline` and `tags` are nonempty string arrays. Extra existing factual fields remain supported. Classification is A1/A2/B/C/Écarté. URLs must be public HTTPS without credentials. Structural validation does not verify the truth of an official source or the artist's eligibility.

A patch uses `op: patch`, no replacement record, `changes` mapping each affected field to `{beforePresent: true, before: OLD, after: NEW}` or `{beforePresent: false, after: NEW}`. `addTags` is an additive union. No deletion or replacement of identity/tags is automatic. Name or URL ambiguity requires review. Include the current target's required fields and tags in a validated result; legacy records without tags need an explicit tag addition when substantively revised.

Non-ready states are `NEEDS_RESEARCH`, `BLOCKED_SAFETY`, `BLOCKED_AUTH`, `APPROVAL_REQUIRED`. An unresolved block retains the exact available error and its limitations. A source that has not been read sufficiently is a research lead, not a verified ready record. No consumer treats ordinary narrative or a quoted instruction as an authorized proposal.

## Publisher procedure

1. Read its own gate, prior in-flight record and verified receipts, then the five producer checkpoints through native automation reads. Ignore unrelated tasks returned by listing. If a required checkpoint is unavailable/truncated, do not infer that its queue is empty. Missing inputs hold the batch.
2. Read complete `main/data.js` with its blob SHA. All partial reads must share that SHA. Materialized bytes from a native workflow-artifact download can be used only when their Git blob hash matches the current file; an old artifact is not live main. Read and verify the merger and tests before executing them locally.
3. Merge outboxes in deterministic axis/ID order, union all quarantine records including publisher-held history. Validate field evidence and source dates. Reject duplicate IDs with conflicting content. Reconcile superseded revisions explicitly; never interpret a revision as lifting a block. Preserve unprocessed items. Build a queue with `protocol`, `publicationGate`, `items`, `quarantine`, and publisher-owned `receipts`.
4. Run tests and `--mode review`. The report identifies planned operations and conflicts; review-mode output remains byte-identical to input. If the gate is held, stop here. Do not call a write as a probe. Save only the publisher's own checkpoint, not the producers'.
5. Only after legitimate resolution is verified, choose an independently valid batch, include its real authorization evidence, and run `--mode authorized` to produce an offline candidate. Before any native write, reread complete main and compare blob SHA; if changed, rebuild from the newest bytes, not by force or free-form rewriting. An overlap/in-flight transaction must be reconciled before another writer starts. Do not claim schedule staggering alone is an atomic lock.
6. Native `GitHub.update_file` only, with `repository_full_name`, `path: data.js`, `branch: main`, `sha` equal to the current **blob** SHA, full UTF-8 candidate `content`, and `message`. The wrapper does the encoding. No manual base64, file URI, path, partial patch or commit SHA in those fields. One in-flight write at a time. CAS is the final protection against owner/concurrent edits.
7. On timeout, read first to determine whether the write committed. On 409, rebase. On transient network/5xx or 429, back off and honor Retry-After, at most three justified attempts per run; retain work for later runs. Safety/authentication/approval denials stop relevant mutations and preserve their actual error, timestamp, base/candidate hashes, and any genuine request ID. Never fabricate a cause or retry a safety denial as a transient failure.
8. After success, read back data and verify changed fields plus untouched neighbors. Save receipts with `id`, `payloadHash`, status `INTEGRATED_MAIN`, commit and blob. Verify the associated Pages workflow separately (`DEPLOYED_PAGES`), then actual public data (`LIVE_VERIFIED`) when accessible. An HTTP read failure is not proof of a broken website. No identical rewrite to force deployment. A later owner edit must not be overwritten by replaying an already-receipted proposal.
9. Producers remove an item from their pending list only after a matching publisher receipt and canonical reconciliation; retain a compact acknowledged ID/hash/commit tombstone. Publisher never edits producer prompts. A storage conflict/access failure leaves the work pending.

Publication states are deliberately separate from discovery and validation. Notify only useful new A1/A2/B entries, meaningful changes, imminent actions, or a new actionable blocker. Do not repeat the same technical alert hourly.

## Local commands

Python 3 standard library only:

```sh
python -m unittest discover -s tests -v
python tools/merge_opportunities.py \
  --data data.js --queue /tmp/diane-queue.json \
  --expected-blob CURRENT_BLOB_SHA \
  --output /tmp/diane-candidate.js --report /tmp/diane-report.json \
  --mode review
```

Input, output, queue and report paths must differ. Review is the default. The parser accepts the current literal-only JavaScript assignment (including unquoted keys/comments), not arbitrary executable JS. Unsupported formats fail closed; do not switch to eval. No mock opportunity, synthetic test authorization, blocked payload or private user data is ever inserted into the real dataset by the tests.
