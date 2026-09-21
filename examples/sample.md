# Sample docs for docs-exec

This file exercises `docs-exec`. It intentionally contains passing,
failing, and skipped blocks so tests can assert exit-code behavior.

## Passing

```bash
echo "hello from docs-exec"
test -z "$FOO_UNSET_FOR_DOCS_EXEC"
```

```sh
echo "sh blocks run too"
```

## Failing

```bash
echo "this block fails on purpose"
exit 1
```

## Skipped via info string

```bash skip-docs-exec
exit 99
```

## Skipped via HTML comment

<!-- docs-exec:skip -->

```bash
exit 99
```

## Ignored language

```python
print("docs-exec only runs bash/sh/shell")
```
