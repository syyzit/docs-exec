"""Extract fenced code blocks from markdown files (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_LANGS = ("bash", "sh", "shell")

SKIP_INFO_TOKENS = ("skip-docs-exec", "docs-exec:skip")
SKIP_HTML_COMMENT = "<!-- docs-exec:skip -->"


@dataclass
class Block:
    """A single fenced code block extracted from a markdown file."""

    file: str
    index: int  # 1-based position among executable blocks in this file
    lang: str  # normalized: bash | sh | shell
    info: str  # raw info string after the opening fence
    code: str
    line: int  # 1-based line number of the opening fence
    end_line: int  # 1-based line number of the closing fence
    skipped: bool = False


def _is_executable_lang(info: str) -> str | None:
    first = info.strip().split(maxsplit=1)[0] if info.strip() else ""
    lang = first.lower()
    if lang in SUPPORTED_LANGS:
        return lang
    return None


def _info_requests_skip(info: str) -> bool:
    lowered = info.lower()
    return any(token in lowered for token in SKIP_INFO_TOKENS)


def _comment_requests_skip(lines: list[str], fence_lineno: int) -> bool:
    """Check the few lines above the fence for a skip HTML comment."""
    start = max(0, fence_lineno - 4)
    for line in lines[start:fence_lineno]:
        if SKIP_HTML_COMMENT in line:
            return True
    return False


def extract_blocks_from_text(text: str, filename: str = "<stdin>") -> list[Block]:
    """Extract executable fenced blocks from markdown text.

    Supports ``` and ~~~ fences. Non-executable languages are ignored.
    Blocks are marked skipped when the info string contains a skip token
    (e.g. ```bash skip-docs-exec) or when preceded by <!-- docs-exec:skip -->.
    """
    lines = text.splitlines()
    blocks: list[Block] = []
    counter = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip(" ")
        indent = len(line) - len(line.lstrip(" "))
        fence = None
        if indent <= 3 and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence_char = stripped[0]
            j = 0
            while j < len(stripped) and stripped[j] == fence_char:
                j += 1
            fence = fence_char * j
        if fence is None:
            i += 1
            continue

        info = stripped[len(fence):].strip()
        # A closing fence never carries an info string; treat lone closings
        # as plain text and only open a block when there is a plausible open.
        # (We accept any open fence here and decide executability below.)
        opening_lineno0 = i  # 0-based
        i += 1
        code_lines: list[str] = []
        closed = False
        while i < n:
            candidate = lines[i]
            c_stripped = candidate.strip()
            if (
                len(candidate) - len(candidate.lstrip(" ")) <= 3
                and c_stripped.startswith(fence[0])
                and set(c_stripped) <= {fence[0]}
                and len(c_stripped) >= len(fence)
            ):
                closed = True
                break
            code_lines.append(candidate)
            i += 1

        end_lineno0 = i if closed else n - 1
        if closed:
            i += 1  # consume closing fence

        lang = _is_executable_lang(info)
        if lang is None:
            continue

        counter += 1
        skipped = _info_requests_skip(info) or _comment_requests_skip(
            lines, opening_lineno0
        )
        blocks.append(
            Block(
                file=filename,
                index=counter,
                lang=lang,
                info=info,
                code="\n".join(code_lines) + ("\n" if code_lines else ""),
                line=opening_lineno0 + 1,
                end_line=end_lineno0 + 1,
                skipped=skipped,
            )
        )
        # If the fence was never closed, stop: the rest was consumed as code.
        if not closed:
            break
    return blocks


def extract_blocks_from_file(path: Path) -> list[Block]:
    """Read a markdown file and extract its executable blocks.

    Raises OSError / UnicodeDecodeError to the caller for exit-code mapping.
    """
    text = path.read_text(encoding="utf-8")
    return extract_blocks_from_text(text, filename=str(path))
