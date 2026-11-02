#!/usr/bin/env python3
"""
Run and validate the COBOL banking application inside the prebuilt
BuildPiper execution container.

The container image is expected to already contain GnuCOBOL, GCC, Make,
Python 3 and the other required utilities. This script does NOT:
  - build or inspect a Dockerfile
  - build, tag or push a Docker image
  - invoke Docker or require access to the Docker daemon

It validates the checked-out project, builds the COBOL application, generates
sample data, runs the application, executes the automated test suite and\ngenerates a SHA-256 checksum for the compiled executable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Sequence


class Logger:
    COLORS = {
        "INFO": "\033[36m",
        "PASS": "\033[32m",
        "TEST": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "DEBUG": "\033[90m",
        "RESET": "\033[0m",
    }

    def __init__(self, log_path: Path, *, use_color: bool, debug: bool) -> None:
        self.log_path = log_path
        self.use_color = use_color and sys.stdout.isatty() and "NO_COLOR" not in os.environ
        self.debug_enabled = debug
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.log_path.open("a", encoding="utf-8")

    @staticmethod
    def timestamp() -> str:
        return dt.datetime.now().astimezone().isoformat(timespec="seconds")

    def _write(self, level: str, message: str) -> None:
        plain = f"{self.timestamp()} [{level}] {message}"
        color = self.COLORS.get(level, "")
        prefix = color if color and self.use_color else ""
        suffix = self.COLORS["RESET"] if prefix else ""
        print(f"{prefix}{plain}{suffix}", flush=True)
        self._stream.write(plain + "\n")
        self._stream.flush()

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def pass_(self, message: str) -> None:
        self._write("PASS", message)

    def test(self, message: str) -> None:
        self._write("TEST", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def debug(self, message: str) -> None:
        if self.debug_enabled:
            self._write("DEBUG", message)

    def close(self) -> None:
        self._stream.close()


class RunSummary:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger
        self.started = time.monotonic()
        self.results: list[tuple[str, str, float, str]] = []
        self.overall_status = "RUNNING"

    @contextmanager
    def stage(self, name: str):
        started = time.monotonic()
        self.logger.info(f"========== {name} ==========")
        try:
            yield
        except Exception as exc:
            self.results.append((name, "FAILED", time.monotonic() - started, str(exc)))
            raise
        else:
            self.results.append((name, "PASSED", time.monotonic() - started, ""))

    def skipped(self, name: str, reason: str) -> None:
        self.results.append((name, "SKIPPED", 0.0, reason))

    def finish(self, status: str) -> None:
        self.overall_status = status

    def print_summary(self, log_file: Path) -> None:
        total = time.monotonic() - self.started
        self.logger.info("")
        self.logger.info("============================================================")
        if self.overall_status == "PASSED":
            self.logger.pass_("                    EXECUTION SUMMARY")
        else:
            self.logger.error("                    EXECUTION SUMMARY")
        self.logger.info(f"Overall status : {self.overall_status}")
        self.logger.info(f"Total duration : {total:.2f} seconds")
        self.logger.info("------------------------------------------------------------")
        for name, status, duration, detail in self.results:
            line = f"{name:<30} {status:<8} {duration:>7.2f}s"
            if status == "PASSED":
                self.logger.pass_(line)
            elif status == "FAILED":
                self.logger.error(line)
                if detail:
                    self.logger.error(f"  Reason: {detail}")
            else:
                self.logger.warning(line + (f" ({detail})" if detail else ""))
        self.logger.info("------------------------------------------------------------")
        self.logger.info(f"Detailed log    : {log_file}")
        self.logger.info("============================================================")


class CommandFailure(RuntimeError):
    def __init__(self, command: Sequence[str], return_code: int) -> None:
        self.return_code = return_code
        super().__init__(
            f"Command exited with status {return_code}: {' '.join(map(str, command))}"
        )


def run_command(
    command: Sequence[str],
    logger: Logger,
    *,
    cwd: Path,
    output_level: str = "INFO",
) -> None:
    logger.info(f"Executing: {' '.join(map(str, command))}")
    try:
        process = subprocess.Popen(
            list(map(str, command)),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        logger.error(f"Unable to start command: {exc}")
        raise

    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            line = raw_line.rstrip("\r\n")
            if line:
                if output_level == "TEST":
                    logger.test(f"  {line}")
                else:
                    logger.info(f"  {line}")
    except KeyboardInterrupt:
        logger.warning("Interrupt received; terminating active command.")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    finally:
        process.stdout.close()

    return_code = process.wait()
    if return_code:
        logger.error(f"Command failed with exit code {return_code}.")
        raise CommandFailure(command, return_code)
    logger.info("Command completed successfully.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and test the COBOL application inside the prebuilt BuildPiper container."
    )
    parser.add_argument(
        "--context",
        default=None,
        help="Project directory. Defaults to the directory containing this script.",
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (default: <project>/logs/cobol-validation-<timestamp>.log).",
    )
    parser.add_argument(
        "--skip-app-tests",
        action="store_true",
        help="Skip COBOL compilation, application execution and automated tests.",
    )
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI console colors.")
    parser.add_argument("--debug", action="store_true", help="Enable diagnostic debug logs.")
    return parser.parse_args()


def resolve_project(args: argparse.Namespace) -> Path:
    if args.context is None:
        return Path(__file__).resolve().parent
    context = Path(args.context).expanduser()
    return context.resolve() if context.is_absolute() else (Path.cwd() / context).resolve()


def validate_project(project: Path, skip_app_tests: bool, logger: Logger) -> None:
    if not project.is_dir():
        raise ValueError(f"Project directory does not exist: {project}")

    required_files = [
        "Makefile",
        "src/main.cob",
        "src/validate-transaction.cob",
        "src/validate-account.cob",
        "src/check-transaction-limit.cob",
        "src/calculate-service-fee.cob",
        "src/update-account.cob",
        "copybooks/account-record.cpy",
        "copybooks/account-table.cpy",
        "copybooks/transaction-record.cpy",
        "tests/test.sh",
        "scripts/create-sample-data.py",
    ]
    if not skip_app_tests:
        missing = [name for name in required_files if not (project / name).is_file()]
        if missing:
            raise ValueError("Required project files are missing: " + ", ".join(missing))
    logger.pass_("Project structure validated.")


def validate_runtime(logger: Logger) -> None:
    # These dependencies are expected to be baked into the prebuilt execution image.
    required_commands = ["cobc", "gcc", "make", "python3", "bash"]
    missing = [name for name in required_commands if shutil.which(name) is None]
    if missing:
        raise RuntimeError(
            "Required tools are missing from the running container: "
            + ", ".join(missing)
            + ". Add them to the BuildPiper execution image."
        )
    logger.pass_("Required runtime tools are available in the current container.")
    for command in required_commands:
        logger.debug(f"{command}: {shutil.which(command)}")



def generate_artifact_checksum(project: Path, logger: Logger, summary: RunSummary) -> Path:
    """Generate a SHA-256 checksum for the compiled COBOL executable."""
    artifact = project / "build" / "banking-app"
    checksum_file = project / "build" / "banking-app.sha256"

    with summary.stage("Artifact checksum generation"):
        if not artifact.is_file():
            raise FileNotFoundError(
                f"Compiled artifact not found: {artifact}. Run the build stage first."
            )

        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)

        checksum = digest.hexdigest()
        checksum_file.write_text(
            f"{checksum}  {artifact.name}\\n",
            encoding="utf-8",
        )
        logger.pass_(f"SHA-256: {checksum}")
        logger.pass_(f"Checksum file generated: {checksum_file}")
        return checksum_file


def run_application(project: Path, logger: Logger, summary: RunSummary) -> None:
    stages = [
        ("make clean", ["make", "clean"], "INFO"),
        ("make build", ["make", "build"], "INFO"),
        ("make data", ["make", "data"], "INFO"),
        ("Application execution", ["./build/banking-app"], "TEST"),
        ("Automated test suite", ["bash", "tests/test.sh"], "TEST"),
    ]
    for name, command, level in stages:
        with summary.stage(name):
            if name == "Application execution":
                logger.info("Running COBOL banking application.")
            elif name == "Automated test suite":
                logger.info("Running automated test suite.")
            else:
                logger.info(f"Preparing application: {name}")
            run_command(command, logger, cwd=project, output_level=level)


def main() -> int:
    args = parse_args()
    project = resolve_project(args)
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    log_path = (
        Path(args.log_file).expanduser().resolve()
        if args.log_file
        else project / "logs" / f"cobol-validation-{timestamp}.log"
    )

    try:
        logger = Logger(log_path, use_color=not args.no_color, debug=args.debug)
    except OSError as exc:
        print(f"[ERROR] Cannot initialize log file {log_path}: {exc}", file=sys.stderr)
        return 1

    summary = RunSummary(logger)
    exit_code = 1

    try:
        logger.info("============================================================")
        logger.info("Starting COBOL application validation in the current container.")
        logger.info(f"Project context: {project}")
        logger.info(f"Current working directory: {Path.cwd()}")
        logger.info(f"Script location: {Path(__file__).resolve()}")
        logger.info(f"Log file: {log_path}")
        logger.info("Dockerfile evaluation and Docker image build are disabled.")

        with summary.stage("Project validation"):
            validate_project(project, args.skip_app_tests, logger)

        with summary.stage("Runtime dependency validation"):
            validate_runtime(logger)

        if args.skip_app_tests:
            logger.warning("COBOL application build and tests were skipped.")
            summary.skipped("COBOL application tests", "Skipped by --skip-app-tests")
        else:
            run_application(project, logger, summary)
            generate_artifact_checksum(project, logger, summary)

        logger.pass_("COBOL application validation completed successfully.")
        exit_code = 0

    except KeyboardInterrupt:
        logger.error("Execution interrupted by user.")
        exit_code = 130
    except CommandFailure as exc:
        logger.error(str(exc))
        logger.error("Workflow terminated.")
        exit_code = exc.return_code or 1
    except (OSError, ValueError, RuntimeError) as exc:
        logger.error(str(exc))
        logger.error("Workflow terminated.")
        exit_code = 1
    finally:
        summary.finish("PASSED" if exit_code == 0 else "FAILED")
        summary.print_summary(log_path)
        logger.close()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
