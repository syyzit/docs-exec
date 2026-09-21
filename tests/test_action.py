"""Tests for GitHub Action composite runner (.github/actions/docs-exec/run.py)."""

import importlib.util
import os
import sys
from pathlib import Path
import pytest

RUN_PY_PATH = Path(__file__).parent.parent / ".github" / "actions" / "docs-exec" / "run.py"


def load_run_module():
    spec = importlib.util.spec_from_file_location("action_run", str(RUN_PY_PATH))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def action_mod():
    return load_run_module()


def test_resolve_targets_empty(action_mod):
    assert action_mod.resolve_targets("") is None
    assert action_mod.resolve_targets("   ") is None


def test_resolve_targets_files_and_dirs(action_mod):
    targets = action_mod.resolve_targets("README.md examples/")
    assert targets is not None
    assert "README.md" in targets
    assert any("sample.md" in t for t in targets)


def test_resolve_targets_multiline(action_mod):
    raw = "README.md\nexamples/sample.md"
    targets = action_mod.resolve_targets(raw)
    assert targets == ["README.md", "examples/sample.md"]


def test_resolve_targets_dedup(action_mod):
    raw = "README.md\nREADME.md\nREADME.md"
    targets = action_mod.resolve_targets(raw)
    assert targets == ["README.md"]


def test_parse_summary(action_mod):
    stdout = "PASS foo.md:1 [bash] exit=0\n\n3 passed, 1 failed, 2 skipped.\n"
    passed, failed, skipped = action_mod.parse_summary(stdout)
    assert passed == 3
    assert failed == 1
    assert skipped == 2

    assert action_mod.parse_summary("No executable code blocks found.") == (0, 0, 0)


def test_action_main_passing(action_mod, monkeypatch, tmp_path):
    gh_out = tmp_path / "github_output.txt"
    monkeypatch.setenv("INPUT_PATHS", "README.md")
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    monkeypatch.setenv("INPUT_FAIL_FAST", "false")
    monkeypatch.setenv("INPUT_FAIL_ON_ERROR", "true")

    rc = action_mod.main()
    assert rc == 0

    content = gh_out.read_text(encoding="utf-8")
    assert "passed=1" in content
    assert "failed=0" in content
    assert "exit-code=0" in content


def test_action_main_failing_with_fail_on_error_false(action_mod, monkeypatch, tmp_path):
    gh_out = tmp_path / "github_output.txt"
    monkeypatch.setenv("INPUT_PATHS", "examples/sample.md")
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    monkeypatch.setenv("INPUT_FAIL_FAST", "false")
    monkeypatch.setenv("INPUT_FAIL_ON_ERROR", "false")

    rc = action_mod.main()
    assert rc == 0

    content = gh_out.read_text(encoding="utf-8")
    assert "failed=1" in content
    assert "exit-code=10" in content


def test_action_main_failing_with_fail_on_error_true(action_mod, monkeypatch, tmp_path):
    gh_out = tmp_path / "github_output.txt"
    monkeypatch.setenv("INPUT_PATHS", "examples/sample.md")
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    monkeypatch.setenv("INPUT_FAIL_FAST", "false")
    monkeypatch.setenv("INPUT_FAIL_ON_ERROR", "true")

    rc = action_mod.main()
    assert rc == 10

    content = gh_out.read_text(encoding="utf-8")
    assert "failed=1" in content
    assert "exit-code=10" in content


def test_action_main_fail_fast(action_mod, monkeypatch, tmp_path):
    gh_out = tmp_path / "github_output.txt"
    monkeypatch.setenv("INPUT_PATHS", "examples/sample.md README.md")
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    monkeypatch.setenv("INPUT_FAIL_FAST", "true")
    monkeypatch.setenv("INPUT_FAIL_ON_ERROR", "false")

    rc = action_mod.main()
    assert rc == 0

    content = gh_out.read_text(encoding="utf-8")
    # In fail-fast, sample.md failed, so README.md should not have been run
    assert "passed=2" in content
    assert "failed=1" in content
    assert "total=5" in content
