# docs-exec

Run fenced `bash`/`sh`/`shell` blocks from markdown docs in a fresh temp dir — docs-as-tests for CI and local.

Thin CLI/CI tool. Not an orchestrator. No stage-signal inside this repo (orchestrators may dogfood stage-signal externally around its runs).

## Install

Requires Python 3.11+.

```console
pip install -e .
docs-exec --help
```

## Try it

This block is live — `docs-exec run` executes it in a temp dir:

```bash
echo "docs-exec works"
```

## Usage

```console
# list executable blocks
docs-exec list --files README.md "docs/**/*.md"

# run them (each block in its own temp dir)
docs-exec run --files README.md "docs/**/*.md"

# machine-readable output
docs-exec list --files examples/sample.md --json
docs-exec run --files examples/sample.md --json

# filter languages, set per-block timeout
docs-exec run --files examples/sample.md --lang bash --timeout 30
```

Illustrative transcripts use `console` so the runner ignores them;
only `bash`/`sh`/`shell` fences are executed.

With no `--files` (and no positional files), `docs-exec` discovers `**/*.md`
under the current directory, excluding hidden dirs, `.git`, `.venv`/`venv`,
`node_modules`, and similar.

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | All executed blocks passed (skipped blocks don't fail) |
| `10` | One or more blocks failed (or timed out) |
| `1`  | IO/error (missing/unreadable file, execution environment error) |
| `2`  | Bad args (unknown language, negative timeout, argparse usage error) |

## Skipping blocks

Two easy opt-outs (both reported as `SKIP`, never executed):

````markdown
```bash skip-docs-exec
exit 99
```
````

```markdown
<!-- docs-exec:skip -->

```bash
exit 99
```
```

Any info string containing `skip-docs-exec` or `docs-exec:skip`
(e.g. ```` ```bash docs-exec:skip ````) also skips. A `<!-- docs-exec:skip -->`
comment within ~3 lines above the fence skips that block.

## Example

See [examples/sample.md](examples/sample.md) — it has passing, failing
(intentional `exit 1`, so `docs-exec run --files examples/sample.md`
exits `10`), skipped, and non-bash blocks. Tests assert the
mixed-result behavior; CI dogfoods `list` plus a passing-only run.

## Development

```console
pip install -e ".[dev]"
pytest
```
