from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_CALENDAR_MAP: dict[str, str] = {
    "hourly": "hourly",
    "daily": "daily",
    "weekly": "weekly",
    "monthly": "monthly",
    "yearly": "yearly",
}


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def _require_linux() -> None:
    if not is_linux():
        raise RuntimeError("This function is only available on Linux")


def _require_root() -> None:
    if os.geteuid() != 0:
        raise RuntimeError("This function requires root privileges (run with sudo)")


def _detect_user() -> str:
    try:
        return os.getlogin()
    except (OSError, RuntimeError):
        pass
    user = os.environ.get("USER") or os.environ.get("LOGNAME")
    if user:
        return user
    import pwd

    return pwd.getpwuid(os.getuid()).pw_name


def generate_systemd_service(
    name: str = "ragpipe-serve",
    data_path: str = "./ragpipe_output.json",
    port: int = 7642,
    user: str | None = None,
) -> str:
    _require_linux()

    if user is None:
        user = _detect_user()

    logger.info("Generating systemd service: name=%s user=%s port=%d", name, user, port)

    working_directory = os.path.abspath(".")
    exec_start = f"/usr/bin/env ragpipe serve {data_path} --port {port}"

    lines = [
        "[Unit]",
        f"Description=RAGPipe Server ({name})",
        "After=network.target",
        "",
        "[Service]",
        "Type=simple",
        "Restart=on-failure",
        "RestartSec=5",
        f"User={user}",
        f"WorkingDirectory={working_directory}",
        f"ExecStart={exec_start}",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ]

    return "\n".join(lines)


def generate_systemd_timer(
    name: str = "ragpipe-index",
    project_path: str = ".",
    interval: str = "hourly",
) -> str:
    _require_linux()

    calendar = _CALENDAR_MAP.get(interval, interval)
    logger.info("Generating systemd timer: name=%s interval=%s", name, calendar)

    working_directory = os.path.abspath(project_path)
    exec_start = f"/usr/bin/env ragpipe index {project_path}"

    service_content = "\n".join(
        [
            "[Unit]",
            f"Description=RAGPipe Indexer ({name})",
            "",
            "[Service]",
            "Type=oneshot",
            f"WorkingDirectory={working_directory}",
            f"ExecStart={exec_start}",
            "",
        ]
    )

    timer_content = "\n".join(
        [
            "[Unit]",
            f"Description=RAGPipe Index Timer ({name})",
            "",
            "[Timer]",
            f"OnCalendar={calendar}",
            "Persistent=true",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )

    return timer_content


def generate_systemd_timer_service(
    name: str = "ragpipe-index",
    project_path: str = ".",
) -> str:
    _require_linux()

    working_directory = os.path.abspath(project_path)
    exec_start = f"/usr/bin/env ragpipe index {project_path}"

    return "\n".join(
        [
            "[Unit]",
            f"Description=RAGPipe Indexer ({name})",
            "",
            "[Service]",
            "Type=oneshot",
            f"WorkingDirectory={working_directory}",
            f"ExecStart={exec_start}",
            "",
        ]
    )


def install_service(
    service_content: str,
    timer_content: str | None = None,
    name: str = "ragpipe-serve",
) -> dict:
    _require_linux()
    _require_root()

    import shutil

    systemd_dir = "/etc/systemd/system"
    if not os.path.isdir(systemd_dir):
        raise RuntimeError(f"Systemd directory not found: {systemd_dir}")

    service_path = os.path.join(systemd_dir, f"{name}.service")

    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        os.chmod(service_path, 0o644)
        logger.info("Wrote service file: %s", service_path)
    except OSError as exc:
        raise RuntimeError(f"Failed to write service file to {service_path}: {exc}") from exc

    timer_path: str | None = None
    if timer_content is not None:
        timer_path = os.path.join(systemd_dir, f"{name}.timer")
        try:
            with open(timer_path, "w") as f:
                f.write(timer_content)
            os.chmod(timer_path, 0o644)
            logger.info("Wrote timer file: %s", timer_path)
        except OSError as exc:
            raise RuntimeError(f"Failed to write timer file to {timer_path}: {exc}") from exc

    result: dict = {
        "service_path": service_path,
        "timer_path": timer_path,
        "instructions": [
            "systemctl daemon-reload",
            f"systemctl enable {name}.service",
            f"systemctl start {name}.service",
        ],
    }

    if timer_path is not None:
        result["instructions"].extend(
            [
                f"systemctl enable {name}.timer",
                f"systemctl start {name}.timer",
            ]
        )

    return result
