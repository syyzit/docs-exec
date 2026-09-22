# Dogfood: docs-exec against another repo's markdown

Thin external check (GitHub issue #7): run `docs-exec` against a real
project's docs instead of only this repo's own fixtures.

## Target

A local clone of `syyzit/stage-signal` — its `README.md` plus
`docs/**/*.md` (`CALLER.md`, `COMPOSE.md`, `RELEASE.md`; `SPEC.md`,
`PRIOR_ART.md` and `ROADMAP-1.0.md` contain no `bash`/`sh`/`shell`
fences, only bare or `python`/`yaml` ones, so they contribute zero
blocks). Example invocation from a checkout of this repo:

```console
docs-exec list --files <stage-signal-checkout>/README.md "<stage-signal-checkout>/docs/**/*.md"
docs-exec run --files <stage-signal-checkout>/README.md "<stage-signal-checkout>/docs/**/*.md"
```

## Evidence

- `docs-exec list`: exit `0`, **22 blocks** found (7 in `README.md`,
  5 in `CALLER.md`, 3 in `COMPOSE.md`, 7 in `RELEASE.md`).
- `docs-exec run`: exit `10`, **6 passed, 16 failed, 0 skipped**.

## Findings

All 16 failures are environmental, not `docs-exec` bugs — each block
runs in a fresh temp dir by design, while the target blocks assume a
live repo checkout:

- `pip install -e ".[dev]"` / `.venv/bin/...` references: no checkout
  or venv exists in the temp dir.
- `stage-signal init/start/...` snippets: no initialized
  `.stage-signal/` state in the temp dir.
- `$(git rev-parse HEAD)`, `git tag`, `git log`: temp dir is not a
  git repo.
- `gh attestation verify dist/...`: no `dist/` artifacts, and the
  block uses a `<version>` placeholder.
- Narrative quick-start blocks mix several scenarios (including an
  expected `wait --needs-reclaim` miss and `supervise` after `done`),
  so they cannot pass verbatim anywhere.

No code fix resulted: discovery, per-block isolation, exit codes, and
the pass/fail/skip summary all behaved as specified. The actionable
takeaway is for doc authors: blocks that need repo context (a venv, a
checkout, credentials, placeholders) should opt out with
` ```bash skip-docs-exec ` or a `<!-- docs-exec:skip -->` comment
above the fence — see "Skipping blocks" in the README.
