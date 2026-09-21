# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-09-21

Initial public bootstrap.

- `docs-exec list`: list fenced `bash`/`sh`/`shell` blocks (`--files`, `--lang`, `--json`).
- `docs-exec run`: execute each block in a fresh temp dir (`--files`, `--lang`, `--json`, `--timeout`).
- Exit codes: `0` all passed, `10` one or more blocks failed, `1` IO/error, `2` bad args.
- Skip support: info-string tokens (`skip-docs-exec`, `docs-exec:skip`) and `<!-- docs-exec:skip -->`.
- `examples/sample.md` with pass/fail/skip/ignored cases; pytest suite; GitHub Actions CI (Ubuntu, Python 3.11+).
