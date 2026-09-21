#!/usr/bin/env python3
"""Runner script for docs-exec GitHub Action composite."""

from __future__ import annotations

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SUMMARY_RE = re.compile(r"(\d+)\s+passed,\s+(\d+)\s+failed,\s+(\d+)\s+skipped")


def resolve_targets(raw_paths: str) -> list[str] | None:
    """Resolve raw paths/globs/directories into a list of file paths."""
    raw = raw_paths.strip()
    if not raw:
        return None

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    tokens: list[str] = []
    for line in lines:
        if " " in line:
            tokens.extend(shlex.split(line))
        else:
            tokens.append(line)

    resolved: list[str] = []
    for token in tokens:
        p = Path(token)
        if p.is_dir():
            matched = sorted(str(m) for m in p.rglob("*.md"))
            if matched:
                resolved.extend(matched)
            else:
                resolved.append(token)
        else:
            matched = sorted(glob.glob(token, recursive=True))
            if matched:
                resolved.extend(matched)
            else:
                resolved.append(token)

    seen: set[str] = set()
    unique: list[str] = []
    for item in resolved:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def parse_summary(stdout: str) -> tuple[int, int, int]:
    """Parse '(N) passed, (N) failed, (N) skipped' from stdout."""
    m = SUMMARY_RE.search(stdout)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 0, 0, 0


def set_github_output(name: str, value: Any) -> None:
    """Write output parameter to GITHUB_OUTPUT environment file."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def write_github_summary(
    passed: int, failed: int, skipped: int, total: int, exit_code: int
) -> None:
    """Append summary Markdown to GITHUB_STEP_SUMMARY environment file."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        status_badge = "Passed" if exit_code == 0 else "Failed"
        summary_md = (
            f"### docs-exec Results: {status_badge}\n\n"
            f"| Metric | Count |\n"
            f"|---|---|\n"
            f"| **Passed** | {passed} |\n"
            f"| **Failed** | {failed} |\n"
            f"| **Skipped** | {skipped} |\n"
            f"| **Total** | {total} |\n"
            f"| **Exit Code** | {exit_code} |\n\n"
        )
        try:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write(summary_md)
        except OSError:
            pass


def get_cmd_prefix(action_dir: Path | None) -> tuple[list[str], dict[str, str]]:
    """Determine how to invoke docs-exec and return (cmd, env)."""
    env = os.environ.copy()

    # 1. If docs-exec is already in PATH
    if shutil.which("docs-exec"):
        return ["docs-exec"], env

    # Also check if docs-exec executable is next to the running python
    py_bin_dir = Path(sys.executable).parent
    candidate_bin = py_bin_dir / "docs-exec"
    if candidate_bin.is_file() and os.access(candidate_bin, os.X_OK):
        return [str(candidate_bin)], env

    # 2. Look for repository root (checked out action or caller repo)
    repo_root: Path | None = None
    if action_dir and action_dir.is_dir():
        # action is in .github/actions/docs-exec -> parents[2] is repo root
        candidate = action_dir.resolve().parents[2]
        if (candidate / "pyproject.toml").is_file():
            repo_root = candidate

    if not repo_root:
        candidate = Path.cwd().resolve()
        if (candidate / "pyproject.toml").is_file():
            repo_root = candidate

    # 3. If local source is available, check/install or invoke as module
    if repo_root:
        # Try pip install into the current environment
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", str(repo_root)],
            capture_output=True,
            text=True,
        )
        if shutil.which("docs-exec"):
            return ["docs-exec"], env
        if candidate_bin.is_file() and os.access(candidate_bin, os.X_OK):
            return [str(candidate_bin)], env

        # If src/docs_exec is present, run directly with python -m docs_exec
        if (repo_root / "src" / "docs_exec").is_dir():
            src_path = str(repo_root / "src")
            curr_pypath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_path}:{curr_pypath}" if curr_pypath else src_path
            return [sys.executable, "-m", "docs_exec"], env

    # 4. Fallback: try installing from git (for external caller without local checkout)
    print("[docs-exec-action] docs-exec not in PATH; installing from git...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "git+https://github.com/syyzit/docs-exec.git",
        ],
        capture_output=True,
        text=True,
    )
    if shutil.which("docs-exec"):
        return ["docs-exec"], env

    # Default fallback
    return ["docs-exec"], env


def main() -> int:
    action_path_env = os.environ.get("ACTION_PATH")
    action_dir = Path(action_path_env) if action_path_env else None

    raw_paths = os.environ.get("INPUT_PATHS", "")
    fail_fast_str = os.environ.get("INPUT_FAIL_FAST", "false").strip().lower()
    fail_fast = fail_fast_str in ("true", "1", "yes")

    timeout_str = os.environ.get("INPUT_TIMEOUT", "60").strip()
    timeout = timeout_str if timeout_str else "60"

    lang = os.environ.get("INPUT_LANG", "").strip()

    fail_on_error_str = os.environ.get("INPUT_FAIL_ON_ERROR", "true").strip().lower()
    fail_on_error = fail_on_error_str not in ("false", "0", "no")

    cmd_prefix, env = get_cmd_prefix(action_dir)
    files = resolve_targets(raw_paths)

    total_passed = 0
    total_failed = 0
    total_skipped = 0
    final_exit_code = 0

    if not fail_fast:
        # Run all files at once (or default auto-discovery)
        run_cmd = list(cmd_prefix) + ["run"]
        if files is not None:
            run_cmd.extend(["--files"] + files)
        if timeout:
            run_cmd.extend(["--timeout", timeout])
        if lang:
            run_cmd.extend(["--lang", lang])

        print(f"[docs-exec-action] {' '.join(run_cmd)}")
        res = subprocess.run(run_cmd, capture_output=True, text=True, env=env)
        if res.stdout:
            sys.stdout.write(res.stdout)
            sys.stdout.flush()
        if res.stderr:
            sys.stderr.write(res.stderr)
            sys.stderr.flush()

        p, f, s = parse_summary(res.stdout)
        total_passed = p
        total_failed = f
        total_skipped = s
        final_exit_code = res.returncode
    else:
        # Fail-fast: run file by file
        file_list: list[str] = []
        if files is not None:
            file_list = files
        else:
            # Query default list of files via `list --json`
            list_cmd = list(cmd_prefix) + ["list", "--json"]
            if lang:
                list_cmd.extend(["--lang", lang])
            list_res = subprocess.run(list_cmd, capture_output=True, text=True, env=env)
            if list_res.returncode == 0 and list_res.stdout.strip():
                try:
                    blocks = json.loads(list_res.stdout)
                    seen_files: set[str] = set()
                    for b in blocks:
                        f_name = b.get("file")
                        if f_name and f_name not in seen_files:
                            seen_files.add(f_name)
                            file_list.append(f_name)
                except Exception:
                    file_list = []

        if not file_list:
            # Run once to show default message / handle empty case
            run_cmd = list(cmd_prefix) + ["run"]
            if timeout:
                run_cmd.extend(["--timeout", timeout])
            if lang:
                run_cmd.extend(["--lang", lang])
            res = subprocess.run(run_cmd, capture_output=True, text=True, env=env)
            if res.stdout:
                sys.stdout.write(res.stdout)
                sys.stdout.flush()
            if res.stderr:
                sys.stderr.write(res.stderr)
                sys.stderr.flush()
            p, f, s = parse_summary(res.stdout)
            total_passed = p
            total_failed = f
            total_skipped = s
            final_exit_code = res.returncode
        else:
            for file_path in file_list:
                run_cmd = list(cmd_prefix) + ["run", "--files", file_path]
                if timeout:
                    run_cmd.extend(["--timeout", timeout])
                if lang:
                    run_cmd.extend(["--lang", lang])

                print(f"[docs-exec-action] {' '.join(run_cmd)}")
                res = subprocess.run(run_cmd, capture_output=True, text=True, env=env)
                if res.stdout:
                    sys.stdout.write(res.stdout)
                    sys.stdout.flush()
                if res.stderr:
                    sys.stderr.write(res.stderr)
                    sys.stderr.flush()

                p, f, s = parse_summary(res.stdout)
                total_passed += p
                total_failed += f
                total_skipped += s

                if res.returncode != 0:
                    final_exit_code = res.returncode
                    print(
                        f"\n[docs-exec-action] fail-fast: halting after failure in {file_path}",
                        file=sys.stderr,
                    )
                    break

    total = total_passed + total_failed + total_skipped
    set_github_output("passed", total_passed)
    set_github_output("failed", total_failed)
    set_github_output("skipped", total_skipped)
    set_github_output("total", total)
    set_github_output("exit-code", final_exit_code)
    write_github_summary(total_passed, total_failed, total_skipped, total, final_exit_code)

    if fail_on_error and final_exit_code != 0:
        return final_exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
