# docs-exec

Run fenced `bash`/`sh`/`shell` blocks from markdown docs in a fresh temp dir — docs-as-tests for CI and local.

Thin CLI/CI tool. Not an orchestrator. No stage-signal inside this repo (orchestrators may dogfood stage-signal externally around its runs).

## Install

Requires Python 3.11+ and pip 21.3+ with setuptools 64+ (PEP 660 editable installs) — upgrade first on fresh venvs.

```console
python -m pip install --upgrade pip setuptools
pip install -e ".[dev]"
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

## GitHub Action

Run `docs-exec` as a composite GitHub Action in CI to test markdown code blocks:

```yaml
name: docs-test
on: [push, pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: syyzit/docs-exec/.github/actions/docs-exec@main
        with:
          paths: README.md
```

### Action inputs

| Input | Description | Default |
|-------|-------------|---------|
| `paths` | Markdown files, directories, or globs to test (space or newline separated). If omitted, discovers all `**/*.md`. | `""` |
| `fail-fast` | If `true`, stops immediately on the first failing file. | `false` |
| `python-version` | Python version to set up via `actions/setup-python` (set to `""` to use runner's ambient Python). | `'3.11'` |
| `timeout` | Per-block timeout in seconds (`0` disables timeout). | `60` |
| `lang` | Filter languages to run (e.g. `bash`, `sh`, or `bash,sh`). | `""` (all supported) |
| `fail-on-error` | Exit with a non-zero code if any block fails. Set to `false` for audit/reporting runs. | `true` |

### Action outputs

| Output | Description |
|--------|-------------|
| `passed` | Total number of passed blocks |
| `failed` | Total number of failed blocks |
| `skipped` | Total number of skipped blocks |
| `total` | Total number of evaluated blocks |
| `exit-code` | Exit code from `docs-exec` (`0`, `10`, `1`, or `2`) |

### Multi-path and fail-fast example

```yaml
- uses: syyzit/docs-exec/.github/actions/docs-exec@main
  with:
    paths: |
      README.md
      docs/
      examples/
    fail-fast: true
```

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

## Dogfood

External check against another repo's markdown (a `stage-signal`
checkout: `README.md` + `docs/**/*.md`): `list` found 22 blocks,
`run` exited `10` with 6 passed / 16 failed / 0 skipped — every
failure traced to the target blocks assuming a live repo checkout
(venv, `.git`, initialized tool state, `dist/` artifacts), which the
per-block temp dir intentionally does not provide. Details:
[docs/DOGFOOD.md](docs/DOGFOOD.md).

## Development

```console
python -m pip install --upgrade pip setuptools
pip install -e ".[dev]"
pytest
```
