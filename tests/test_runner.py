"""Runner unit tests."""

from docs_exec.extract import extract_blocks_from_text
from docs_exec.runner import run_block, run_blocks


def _block(code="echo hi", skipped=False):
    (block,) = extract_blocks_from_text(f"```bash\n{code}\n```\n", filename="t.md")
    block.skipped = skipped
    return block


def test_run_passing_block():
    result = run_block(_block("echo hello"), timeout=10)
    assert result.passed is True
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_run_failing_block():
    result = run_block(_block("exit 3"), timeout=10)
    assert result.passed is False
    assert result.returncode == 3


def test_run_skipped_block_not_executed():
    result = run_block(_block("exit 99", skipped=True), timeout=10)
    assert result.skipped is True
    assert result.passed is True
    assert result.returncode is None


def test_each_block_gets_fresh_temp_dir():
    first = run_block(_block("pwd"), timeout=10)
    second = run_block(_block("pwd"), timeout=10)
    assert first.passed and second.passed
    # Same command, but each run happens in its own temp dir (docs-exec prefix).
    assert "docs-exec-" in first.stdout
    assert "docs-exec-" in second.stdout


def test_timeout_marks_failure():
    result = run_block(_block("sleep 5"), timeout=0.2)
    assert result.passed is False
    assert result.timed_out is True


def test_sample_md_mixed_results():
    from pathlib import Path

    from docs_exec.extract import extract_blocks_from_file

    blocks = extract_blocks_from_file(Path("examples/sample.md"))
    runnable = [b for b in blocks if not b.skipped]
    skipped = [b for b in blocks if b.skipped]
    assert len(runnable) == 3  # 2 pass + 1 fail
    assert len(skipped) == 2
    results = run_blocks(blocks, timeout=10)
    assert sum(1 for r in results if r.passed and not r.skipped) == 2
    assert sum(1 for r in results if not r.passed) == 1
