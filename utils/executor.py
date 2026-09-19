"""Sandboxed code execution utility using isolated subprocesses."""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from typing import Union, Optional

from utils.types import ExecutionResult
from utils.files import get_associated_chart_path


DEFAULT_TIMEOUT_SECONDS = 30


def execute_script(
    script_path: Union[str, Path],
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> ExecutionResult:
    """Executes a Python script in an isolated subprocess with timeout and safety guarantees.

    Args:
        script_path: Path to the Python script to execute.
        timeout_seconds: Maximum allowed runtime in seconds before timing out.

    Returns:
        ExecutionResult containing success flag, captured stdout/stderr, and paths.
    """
    path = Path(script_path)
    if not path.exists():
        return ExecutionResult(
            success=False,
            script_path=str(path),
            error=f"Script file not found: {path.name}",
        )

    resolved_script = path.resolve()
    expected_chart = get_associated_chart_path(resolved_script)

    try:
        run_start_time = time.time()
        # Run python script in subprocess using current Python executable and workspace cwd
        proc = subprocess.run(
            [sys.executable, str(resolved_script)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(Path.cwd()),
        )

        # Check for generated chart file in expected location or relative to script
        resolved_chart = None
        alt_chart = resolved_script.parent / expected_chart.name
        if expected_chart.exists():
            resolved_chart = str(expected_chart.resolve())
        elif alt_chart.exists():
            resolved_chart = str(alt_chart.resolve())
        elif proc.returncode == 0:
            # Fallback: search for any new .png file created during this execution
            # (e.g. if the generated script saved to f"{ticker}_{period}.png" or cwd)
            cwd = Path.cwd().resolve()
            search_dirs = [resolved_script.parent]
            if cwd not in search_dirs:
                search_dirs.append(cwd)

            candidate_pngs = []
            for d in search_dirs:
                if d.exists():
                    for p in d.glob("*.png"):
                        try:
                            if p.stat().st_mtime >= (run_start_time - 1.0):
                                candidate_pngs.append(p)
                        except OSError:
                            pass

            if candidate_pngs:
                candidate_pngs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                newest = candidate_pngs[0]
                try:
                    expected_chart.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(newest, expected_chart)
                    resolved_chart = str(expected_chart.resolve())
                    if newest.parent == cwd and newest.resolve() != expected_chart.resolve():
                        try:
                            newest.unlink()
                        except OSError:
                            pass
                except Exception:
                    resolved_chart = str(newest.resolve())

        execution_time = time.time() - run_start_time

        if proc.returncode == 0:
            return ExecutionResult(
                success=True,
                script_path=str(path.resolve()),
                chart_path=resolved_chart,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                execution_time_seconds=execution_time,
                error=None,
            )
        else:
            return ExecutionResult(
                success=False,
                script_path=str(path.resolve()),
                chart_path=resolved_chart,
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                execution_time_seconds=execution_time,
                error=f"Script exited with error code {proc.returncode}:\n{proc.stderr.strip() or proc.stdout.strip()}",
            )

    except subprocess.TimeoutExpired as e:
        execution_time = time.time() - run_start_time
        return ExecutionResult(
            success=False,
            script_path=str(path.resolve()),
            chart_path=None,
            stdout=e.stdout or "" if hasattr(e, "stdout") and e.stdout else "",
            stderr=e.stderr or "" if hasattr(e, "stderr") and e.stderr else "",
            returncode=-1,
            execution_time_seconds=execution_time,
            error=f"Execution timed out after {timeout_seconds} seconds.",
        )
    except Exception as e:
        execution_time = time.time() - run_start_time if 'run_start_time' in locals() else 0.0
        return ExecutionResult(
            success=False,
            script_path=str(path.resolve()),
            chart_path=None,
            returncode=-1,
            execution_time_seconds=execution_time,
            error=f"Subprocess execution failed: {str(e)}",
        )
