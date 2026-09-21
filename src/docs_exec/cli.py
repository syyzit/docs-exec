"""CLI for docs-exec: list and run fenced bash/sh/shell blocks from markdown."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from . import __version__
from .extract import SUPPORTED_LANGS, Block, extract_blocks_from_file
from .runner import run_blocks

EXIT_OK = 0
EXIT_IO = 1
EXIT_ARGS = 2
EXIT_FAIL = 10

EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".tox"}


def _default_markdown_files() -> list[str]:
    found: list[str] = []
    for path in sorted(Path.cwd().rglob("*.md")):
        parts = set(path.parts)
        if parts & EXCLUDE_DIRS:
            continue
        if any(part.startswith(".") for part in path.relative_to(Path.cwd()).parts[:-1]):
            continue
        found.append(str(path))
    return found


def _resolve_files(positional: list[str], flagged: list[str] | None) -> list[str] | None:
    """Merge positional + --files globs. Returns None when the user gave nothing."""
    raw = list(positional or []) + list(flagged or [])
    if not raw:
        return None
    expanded: list[str] = []
    for pattern in raw:
        matches = sorted(glob.glob(pattern, recursive=True))
        if matches:
            expanded.extend(matches)
        else:
            expanded.append(pattern)  # keep for a clean "not found" error
    # de-dupe, preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for item in expanded:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _parse_lang_filter(value: str | None) -> set[str] | None:
    if value is None:
        return None
    langs: set[str] = set()
    for part in value.replace(",", " ").split():
        lang = part.strip().lower()
        if not lang:
            continue
        if lang not in SUPPORTED_LANGS:
            raise ValueError(
                f"unsupported language {lang!r} (choose from: {', '.join(SUPPORTED_LANGS)})"
            )
        langs.add(lang)
    return langs or None


def _collect_blocks(
    files: list[str] | None, lang_filter: set[str] | None
) -> tuple[list[Block], int | None]:
    """Extract blocks from files. Returns (blocks, error_exit or None)."""
    targets = files if files is not None else _default_markdown_files()
    if files is not None and not targets:
        print("docs-exec: no files matched", file=sys.stderr)
        return [], EXIT_IO
    blocks: list[Block] = []
    for name in targets:
        path = Path(name)
        if not path.is_file():
            print(f"docs-exec: file not found: {name}", file=sys.stderr)
            return [], EXIT_IO
        try:
            file_blocks = extract_blocks_from_file(path)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"docs-exec: cannot read {name}: {exc}", file=sys.stderr)
            return [], EXIT_IO
        for block in file_blocks:
            if lang_filter is not None and block.lang not in lang_filter:
                continue
            blocks.append(block)
    return blocks, None


def _block_to_dict(block: Block) -> dict:
    return {
        "file": block.file,
        "index": block.index,
        "lang": block.lang,
        "info": block.info,
        "line": block.line,
        "end_line": block.end_line,
        "skipped": block.skipped,
        "code": block.code,
    }


def _cmd_list(args: argparse.Namespace) -> int:
    try:
        lang_filter = _parse_lang_filter(args.lang)
    except ValueError as exc:
        print(f"docs-exec: {exc}", file=sys.stderr)
        return EXIT_ARGS
    files = _resolve_files(args.files_positional, args.files)
    blocks, err = _collect_blocks(files, lang_filter)
    if err is not None:
        return err
    if args.json:
        print(json.dumps([_block_to_dict(block) for block in blocks], indent=2))
        return EXIT_OK
    if not blocks:
        print("No executable code blocks found.")
        return EXIT_OK
    for block in blocks:
        n_lines = len(block.code.splitlines())
        flag = " [skipped]" if block.skipped else ""
        print(f"{block.file}:{block.index} [{block.lang}] line {block.line} ({n_lines} lines){flag}")
    return EXIT_OK


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        lang_filter = _parse_lang_filter(args.lang)
    except ValueError as exc:
        print(f"docs-exec: {exc}", file=sys.stderr)
        return EXIT_ARGS
    timeout = args.timeout
    if timeout is not None and timeout <= 0:
        timeout = None
    files = _resolve_files(args.files_positional, args.files)
    blocks, err = _collect_blocks(files, lang_filter)
    if err is not None:
        return err
    results = run_blocks(blocks, timeout=timeout)
    passed = sum(1 for r in results if r.passed and not r.skipped)
    failed = sum(1 for r in results if not r.passed and not r.skipped)
    skipped = sum(1 for r in results if r.skipped)

    if args.json:
        payload = {
            "blocks": [
                {
                    **_block_to_dict(r.block),
                    "passed": r.passed,
                    "returncode": r.returncode,
                    "stdout": r.stdout,
                    "stderr": r.stderr,
                    "duration_s": round(r.duration_s, 3),
                    "timed_out": r.timed_out,
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            },
        }
        print(json.dumps(payload, indent=2))
    else:
        if not results:
            print("No executable code blocks found.")
        for r in results:
            label = f"{r.block.file}:{r.block.index}"
            if r.skipped:
                print(f"SKIP {label} [{r.block.lang}] line {r.block.line}")
                continue
            status = "PASS" if r.passed else "FAIL"
            extra = " (timeout)" if r.timed_out else ""
            rc = f" exit={r.returncode}" if r.returncode is not None else ""
            print(f"{status} {label} [{r.block.lang}]{rc} ({r.duration_s:.2f}s){extra}")
            if not r.passed:
                if r.stdout.strip():
                    print(f"--- stdout ({label}) ---\n{r.stdout.rstrip()}")
                if r.stderr.strip():
                    print(f"--- stderr ({label}) ---\n{r.stderr.rstrip()}")
        print(f"\n{passed} passed, {failed} failed, {skipped} skipped.")

    return EXIT_FAIL if failed else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docs-exec",
        description="Run fenced bash/sh/shell blocks from markdown docs in a temp dir.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("list", "run"):
        p = sub.add_parser(name, help=f"{'List' if name == 'list' else 'Execute'} code blocks.")
        p.add_argument(
            "files_positional",
            nargs="*",
            metavar="FILE",
            help="Markdown files or globs (also accepted via --files).",
        )
        p.add_argument(
            "--files",
            nargs="*",
            default=None,
            metavar="FILE",
            help="Additional markdown files or globs.",
        )
        p.add_argument(
            "--lang",
            default=None,
            metavar="LANG",
            help="Filter languages, e.g. --lang bash or --lang bash,sh (default: bash/sh/shell).",
        )
        p.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of human text.",
        )
        if name == "run":
            p.add_argument(
                "--timeout",
                type=float,
                default=60.0,
                metavar="SECS",
                help="Per-block timeout in seconds (<=0 disables, default: 60).",
            )
        p.set_defaults(func=_cmd_list if name == "list" else _cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run" and args.timeout is not None and args.timeout < 0:
        print("docs-exec: --timeout must be >= 0", file=sys.stderr)
        return EXIT_ARGS
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return EXIT_IO


if __name__ == "__main__":
    sys.exit(main())
