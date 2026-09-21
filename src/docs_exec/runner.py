"""Execute extracted blocks, each in a fresh temp dir (stdlib only)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass

from .extract import Block

BLOCK_SHELL = shutil.which("bash") or shutil.which("sh") or "bash"


@dataclass
class BlockResult:
    block: Block
    passed: bool
    returncode: int | None
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    skipped: bool = False


def run_block(block: Block, timeout: float | None = 60.0) -> BlockResult:
    """Run one block in a fresh temp dir via bash -c. Skipped blocks are not run."""
    if block.skipped:
        return BlockResult(
            block=block,
            passed=True,
            returncode=None,
            stdout="",
            stderr="",
            duration_s=0.0,
            timed_out=False,
            skipped=True,
        )
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="docs-exec-") as tmp:
            try:
                completed = subprocess.run(
                    [BLOCK_SHELL, "-c", block.code],
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                    timeout=timeout if timeout and timeout > 0 else None,
                )
            except subprocess.TimeoutExpired as exc:
                duration = time.monotonic() - started
                out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                return BlockResult(
                    block=block,
                    passed=False,
                    returncode=None,
                    stdout=out,
                    stderr=(err + f"\n[docs-exec] timed out after {timeout}s").strip(),
                    duration_s=duration,
                    timed_out=True,
                )
            duration = time.monotonic() - started
            return BlockResult(
                block=block,
                passed=completed.returncode == 0,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
                duration_s=duration,
            )
    except OSError as exc:  # e.g. tempdir creation or shell spawn failure
        duration = time.monotonic() - started
        return BlockResult(
            block=block,
            passed=False,
            returncode=None,
            stdout="",
            stderr=f"[docs-exec] execution error: {exc}",
            duration_s=duration,
        )


def run_blocks(
    blocks: list[Block], timeout: float | None = 60.0
) -> list[BlockResult]:
    """Run blocks sequentially, each in its own temp dir."""
    return [run_block(block, timeout=timeout) for block in blocks]
