# Release checklist

Conscious 0.1.0 path to PyPI. Draft only — see the guardrail at the bottom.

## Steps

1. **Version bump** — set `version` in `pyproject.toml`
   (currently `0.1.0`); keep `[project]` metadata in sync
   (`description`, `readme`, `requires-python`, `license`, `urls`).
2. **CHANGELOG** — add an entry under `## [x.y.z] - YYYY-MM-DD`
   in `CHANGELOG.md` describing user-visible changes.
3. **CI green** — `pip install -e ".[dev]"` then `pytest -q` locally;
   push the PR and confirm the `ci` + `docs` workflows are green.
4. **Annotated tag** — after merge to `main`, a maintainer creates
   `git tag -a v0.1.0 -m "v0.1.0"` and pushes it (`git push origin v0.1.0`).
5. **GitHub Release** — draft a Release from the tag (release notes
   mirror the CHANGELOG entry). Publishing the Release triggers
   `.github/workflows/publish.yml`.
6. **PyPI Trusted Publishing** — one-time maintainer setup on PyPI:
   project Settings → Publishing → add a pending publisher for
   `syyzit/docs-exec`, workflow file `publish.yml`, environment `pypi`.
   No API tokens or secrets live in this repo — auth is OIDC
   (`permissions: id-token: write`).
7. **Action pin update** — after the first tag, update consumer docs
   from floating `@main` to a pinned ref (`@v0.1.0`, or moving major
   `@v0`). See the note in `README.md`.

## Guardrail

Agents (human or automated) must NOT run `twine upload` / `python -m
build --installer` uploads, must NOT create or push git tags, and must
NOT create GitHub Releases, unless AGLoop explicitly says go. Preparing
this checklist and the draft workflow is the whole of this issue —
publishing itself is out of scope.
