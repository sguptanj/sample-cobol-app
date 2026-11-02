#!/usr/bin/env python3
"""
Build and validate the Ubuntu 26.04 COBOL CI agent image, then optionally push it.

The application validation runs in a temporary copy of the project. This keeps
`make clean` and generated test files from changing or deleting files in the
user's working tree.

Examples:
  ./build_cobol_image.py
  ./build_cobol_image.py --image cobol-build-agent:ubuntu26
  ./build_cobol_image.py --push-to docker.io/USERNAME/cobol-build-agent:ubuntu26
  ./build_cobol_image.py --context /path/to/sample-cobol-app --debug

Registry authentication must be completed separately:
  docker login
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


class Logger:
    """Console logger with optional ANSI colors and plain persistent logs."""

    COLORS = {
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "DEBUG": "\033[36m",      # Cyan
        "RESET": "\033[0m",
    }

    def __init__(self, log_path: Path, *, use_color: bool, debug: bool) -> None:
        self.log_path = log_path
        self.use_color = (
            use_color
            and sys.stdout.isatty()
            and "NO_COLOR" not in os.environ
        )
        self.debug_enabled = debug
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.log_path.open("a", encoding="utf-8")

    @staticmethod
    def timestamp() -> str:
        return dt.datetime.now().astimezone().isoformat(timespec="seconds")

    def _write(self, level: str, message: str) -> None:
        plain = f"{self.timestamp()} [{level}] {message}"
        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"] if color and self.use_color else ""
        prefix = color if color and self.use_color else ""

        print(f"{prefix}{plain}{reset}", flush=True)
        self._stream.write(plain + "\n")
        self._stream.flush()

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def debug(self, message: str) -> None:
        if self.debug_enabled:
            self._write("DEBUG", message)

    def close(self) -> None:
        self._stream.close()


class CommandFailure(RuntimeError):
    def __init__(self, command: Sequence[str], return_code: int) -> None:
        self.command = list(command)
        self.return_code = return_code
        super().__init__(f"Command exited with status {return_code}")


def run_command(
    command: Sequence[str],
    logger: Logger,
    *,
    cwd: Path | None = None,
) -> None:
    """Execute a command and stream combined output to console and log."""
    rendered_command = subprocess.list2cmdline([str(item) for item in command])
    logger.info(f"Executing: {rendered_command}")
    if cwd:
        logger.debug(f"Working directory: {cwd}")

    try:
        process = subprocess.Popen(
            [str(item) for item in command],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        logger.error(f"Could not start command: {exc}")
        raise

    assert process.stdout is not None
    try:
        for output_line in process.stdout:
            output_line = output_line.rstrip("\r\n")
            if output_line:
                # Command output is retained verbatim apart from the log prefix.
                logger.info(f"  {output_line}")
    except KeyboardInterrupt:
        logger.warning("Interrupt received; stopping the active command.")
        process.send_signal(signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    finally:
        process.stdout.close()

    return_code = process.wait()
    if return_code != 0:
        logger.error(f"Command failed with exit code {return_code}.")
        raise CommandFailure(command, return_code)

    logger.info("Command completed successfully.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build, verify, test and optionally publish the COBOL CI image."
    )
    parser.add_argument(
        "--context",
        default=".",
        help="Project directory and Docker build context (default: current directory).",
    )
    parser.add_argument(
        "--dockerfile",
        default="Dockerfile",
        help="Dockerfile path relative to the build context (default: Dockerfile).",
    )
    parser.add_argument(
        "--image",
        default="cobol-build-agent:ubuntu26",
        help="Local image name and tag.",
    )
    parser.add_argument(
        "--push-to",
        help="Optional full registry image reference to tag and push after validation.",
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (default: <context>/logs/image-build-<timestamp>.log).",
    )
    parser.add_argument(
        "--skip-app-tests",
        action="store_true",
        help="Build and verify the image without compiling/testing the COBOL application.",
    )
    parser.add_argument(
        "--allow-untested-push",
        action="store_true",
        help="Explicitly allow --push-to when --skip-app-tests is also supplied.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors in console output.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable additional diagnostic log messages.",
    )
    return parser.parse_args()


def validate_project(context: Path, dockerfile: Path, args: argparse.Namespace) -> None:
    if not context.is_dir():
        raise ValueError(f"Project/build-context directory does not exist: {context}")
    if not dockerfile.is_file():
        raise ValueError(f"Dockerfile does not exist: {dockerfile}")
    if not args.image.strip():
        raise ValueError("--image cannot be empty.")
    if args.push_to is not None and not args.push_to.strip():
        raise ValueError("--push-to cannot be empty.")
    if args.push_to and args.skip_app_tests and not args.allow_untested_push:
        raise ValueError(
            "Refusing to push an untested image. Remove --skip-app-tests or "
            "explicitly add --allow-untested-push."
        )

    if not args.skip_app_tests:
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
        missing = [item for item in required_files if not (context / item).is_file()]
        if missing:
            raise ValueError(
                "Required project files are missing: " + ", ".join(missing)
            )


def verify_image(docker: str, image: str, logger: Logger) -> None:
    """Check OS release and the actual required commands inside the image."""
    verify_script = r"""
set -Eeuo pipefail
grep -q 'VERSION_ID="26.04"' /etc/os-release
cobc --version
gcc --version | head -n 1
make --version | head -n 1
python3 --version
git --version
for tool in bash curl wget tar gzip sha256sum; do
    command -v "$tool" >/dev/null || {
        echo "Required command missing: $tool" >&2
        exit 1
    }
done
"""
    run_command(
        [
            docker, "run", "--rm",
            "--entrypoint", "/bin/bash",
            image, "-lc", verify_script,
        ],
        logger,
    )


def test_application_in_temporary_copy(
    docker: str, image: str, project: Path, logger: Logger
) -> None:
    """
    Test an isolated project copy so `make clean` cannot remove the user's
    existing build outputs, reports or audit log.
    """
    ignored = shutil.ignore_patterns(
        ".git", ".venv", "venv", "__pycache__", "*.pyc",
        "build", "logs", "reports", "artifacts",
    )

    with tempfile.TemporaryDirectory(prefix="cobol-agent-test-") as temp_dir:
        test_project = Path(temp_dir) / "workspace"
        shutil.copytree(project, test_project, ignore=ignored)
        logger.info("Running COBOL compile and tests in an isolated temporary copy.")
        test_script = (
            "set -Eeuo pipefail; "
            "make clean; "
            "make build; "
            "make data; "
            "./build/banking-app; "
            "bash tests/test.sh"
        )
        run_command(
            [
                docker, "run", "--rm",
                "--mount", f"type=bind,source={test_project},target=/workspace",
                "--workdir", "/workspace",
                "--entrypoint", "/bin/bash",
                image, "-lc", test_script,
            ],
            logger,
        )

    logger.info("Temporary test workspace removed; original project files were preserved.")


def main() -> int:
    args = parse_args()
    project = Path(args.context).expanduser().resolve()

    # Validate the project directory before creating a log directory inside it.
    if not project.is_dir():
        print(f"[ERROR] Project directory does not exist: {project}", file=sys.stderr)
        return 1

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    if args.log_file:
        log_path = Path(args.log_file).expanduser().resolve()
    else:
        log_path = project / "logs" / f"image-build-{timestamp}.log"

    try:
        logger = Logger(
            log_path,
            use_color=not args.no_color,
            debug=args.debug,
        )
    except OSError as exc:
        print(f"[ERROR] Cannot initialize log file {log_path}: {exc}", file=sys.stderr)
        return 1

    try:
        logger.info("============================================================")
        logger.info("Starting COBOL BuildPiper agent image workflow.")
        logger.info(f"Project context: {project}")
        logger.info(f"Log file: {log_path}")

        dockerfile_arg = Path(args.dockerfile).expanduser()
        dockerfile = (
            dockerfile_arg.resolve()
            if dockerfile_arg.is_absolute()
            else (project / dockerfile_arg).resolve()
        )
        validate_project(project, dockerfile, args)

        docker = shutil.which("docker")
        if not docker:
            raise RuntimeError("Docker CLI not found. Install Docker and add it to PATH.")

        # Step 2: Check Docker daemon and build the image.
        run_command([docker, "version"], logger)
        run_command(
            [
                docker, "build",
                "--pull",
                "--file", str(dockerfile),
                "--tag", args.image,
                str(project),
            ],
            logger,
        )

        # Step 3: Verify Ubuntu 26.04 and required dependencies in the image.
        verify_image(docker, args.image, logger)

        # Step 4: Compile and test the COBOL application.
        if args.skip_app_tests:
            logger.warning("COBOL application compilation and tests were skipped.")
        else:
            test_application_in_temporary_copy(docker, args.image, project, logger)

        # Step 5: Publish only after successful checks/tests.
        if args.push_to:
            run_command([docker, "tag", args.image, args.push_to], logger)
            run_command([docker, "push", args.push_to], logger)
            logger.info(f"Image successfully pushed: {args.push_to}")
        else:
            logger.info("No registry push requested; image remains available locally.")

        # Step 6: Summarize verified dependencies.
        logger.info(
            "Verified: Ubuntu 26.04, GnuCOBOL, GCC, Make, Python 3, Git, "
            "Bash, curl, wget, tar, gzip and sha256sum."
        )

        # Step 7: Show the image reference and suggested BuildPiper commands.
        buildpiper_image = args.push_to or args.image
        logger.info("BuildPiper image configuration:")
        logger.info(f"  Image reference: {buildpiper_image}")
        logger.info("  Suggested pipeline commands:")
        logger.info("    make clean && make build && make data")
        logger.info("    ./build/banking-app")
        logger.info("    bash tests/test.sh")
        logger.info("Workflow completed successfully.")
        logger.info("============================================================")
        return 0

    except KeyboardInterrupt:
        logger.error("Execution interrupted by user.")
        return 130
    except CommandFailure as exc:
        logger.error(f"Workflow stopped because a command failed (exit {exc.return_code}).")
        return exc.return_code or 1
    except (OSError, ValueError, RuntimeError) as exc:
        logger.error(str(exc))
        logger.error("Workflow terminated.")
        return 1
    finally:
        logger.info(f"Execution log saved to: {log_path}")
        logger.close()


if __name__ == "__main__":
    sys.exit(main())
