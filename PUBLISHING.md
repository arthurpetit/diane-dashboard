# Diane dashboard publication — five independent axis files

## Canonical source

The published dataset is generated from exactly five files:

- `opportunities/axis1.json` — concours & expositions
- `opportunities/axis2.json` — commandes & art public
- `opportunities/axis3.json` — résidences & bourses
- `opportunities/axis4.json` — institutions & acquisitions
- `opportunities/axis5.json` — privé & mécénat

`data.js` is now a generated compatibility artifact. Research routines MUST NOT edit it. The browser interface remains unchanged.

## Rule for each research routine

A routine owns only its axis file. For a substantive validated change:

1. Read fresh `main`, this contract, its own axis JSON, and its live pending checkpoint.
2. Verify the official source and prepare only this axis's additions or factual updates. Preserve unknowns explicitly and do not invent missing payloads.
3. Create a unique temporary branch `diane/axis<N>/<UTC-run-id>` from fresh main.
4. Modify only `opportunities/axis<N>.json`. Preserve all existing records and unrelated fields. Reject duplicate names/URLs.
5. Commit, open a PR to `main`, and verify that the PR changes only that axis file.
6. If main moved, rebuild only this axis delta on current main; never overwrite another axis.
7. Merge, then read back the axis file on main and verify the exact intended delta.
8. Only after verified merge/readback may the corresponding pending item be acknowledged.
9. Delete the temporary branch when a native delete action is available and its head is verified merged. Cleanup failure never replays data.
10. Pages deployment and live verification are separate from Git integration.

Branch, commit, PR, local test, or successful research are not publication.

## Validation and deployment

GitHub Pages runs `test_simple_publication.py`, then:

```sh
python tools/prepare_axis_json.py --output _site
```

The build validates all five JSON files together, refuses duplicate identities, preserves every record from the migration baseline, generates `_site/data.js`, and publishes only `index.html`, `data.js`, and `.nojekyll`.

A malformed axis file or missing baseline record fails deployment instead of silently deleting data. New records are allowed after validation.

## Pending research

Automation prompts remain the recovery source for unpublished discoveries. Preserve every pending payload, source, research lead, superseded revision, validation note, and incomplete legacy reference until its state is reconciled. A reference without its original complete payload stays input-pending; never fabricate it.

Historical failure labels are evidence of what happened at that time, not substitutes for checking current state. An actual current permission/authentication/restriction error applies according to its demonstrated scope and must not be routed around.

## Scope

Do not modify another axis, the ten general filters, UI behavior, repository permissions, credentials, schedules, budgets, or research scope as part of an opportunity publication. No Google Sheet or external service is required.
