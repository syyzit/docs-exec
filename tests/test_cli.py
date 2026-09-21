"""CLI exit-code and output tests."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from docs_exec.cli import EXIT_ARGS, EXIT_FAIL, EXIT_IO, EXIT_OK, main

SAMPLE = Path("examples/sample.md")


def test_list_sample_blocks(capsys):
    assert SAMPLE.exists()
    assert main(["list", "--files", str(SAMPLE)]) == EXIT_OK
    out = capsys.readouterr().out
    assert "bash" in out


def test_list_json_shape(capsys):
    assert main(["list", "--files", str(SAMPLE), "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)
    assert {b["lang"] for b in payload} >= {"bash", "sh"}
    assert sum(1 for b in payload if b["skipped"]) == 2


def test_run_sample_fails_with_exit_10(capsys):
    assert main(["run", "--files", str(SAMPLE), "--timeout", "10"]) == EXIT_FAIL
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "SKIP" in out


def test_run_json_summary(capsys):
    assert main(["run", "--files", str(SAMPLE), "--json", "--timeout", "10"]) == EXIT_FAIL
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"] == {"total": 5, "passed": 2, "failed": 1, "skipped": 2}


def test_run_passing_only_file_exits_zero(tmp_path, capsys):
    doc = tmp_path / "passing.md"
    doc.write_text("# t\n\n```bash\necho ok\n```\n", encoding="utf-8")
    assert main(["run", "--files", str(doc)]) == EXIT_OK
    assert "1 passed" in capsys.readouterr().out


def test_run_missing_file_exits_1(capsys):
    assert main(["run", "--files", "does-not-exist.md"]) == EXIT_IO


def test_bad_lang_exits_2(capsys):
    assert main(["list", "--files", str(SAMPLE), "--lang", "python"]) == EXIT_ARGS


def test_negative_timeout_exits_2(capsys):
    assert main(["run", "--files", str(SAMPLE), "--timeout", "-1"]) == EXIT_ARGS


def test_installed_entrypoint_lists_blocks():
    proc = subprocess.run(
        [sys.executable, "-m", "docs_exec.cli", "list", "--files", str(SAMPLE)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == EXIT_OK
    assert "bash" in proc.stdout


@pytest.mark.skipif(Path("examples/sample.md").exists() is False, reason="needs sample.md")
def test_lang_filter_limits_blocks(capsys):
    assert main(["list", "--files", str(SAMPLE), "--lang", "sh", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload and all(b["lang"] == "sh" for b in payload)
