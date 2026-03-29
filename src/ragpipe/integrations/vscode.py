from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_INDEX_ARGS: dict[str, Any] = {
    "chunk-size": 512,
    "output": "./ragpipe_output.json",
}


def generate_tasks(
    project_path: str = ".",
    output_path: str = ".vscode/tasks.json",
    index_args: dict[str, Any] | None = None,
) -> Path:
    base = Path(project_path).resolve()
    dest = base / output_path if not Path(output_path).is_absolute() else Path(output_path)

    merged_args = {**DEFAULT_INDEX_ARGS, **(index_args or {})}

    index_args_list: list[str] = []
    for k, v in merged_args.items():
        flag = f"--{k}"
        index_args_list.append(flag)
        index_args_list.append(str(v))

    tasks: dict[str, Any] = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "RAGPipe: Index Project",
                "type": "shell",
                "command": "ragpipe",
                "args": ["index", "."] + index_args_list,
                "problemMatcher": [],
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "shared",
                    "showReuseMessage": True,
                    "clear": False,
                },
            },
            {
                "label": "RAGPipe: Query",
                "type": "shell",
                "command": "ragpipe",
                "args": ["query", "${input:ragpipePrompt}"],
                "problemMatcher": [],
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                    "showReuseMessage": True,
                    "clear": True,
                },
            },
            {
                "label": "RAGPipe: Serve",
                "type": "shell",
                "command": "ragpipe",
                "args": ["serve", "--port", "7642"],
                "problemMatcher": [],
                "isBackground": True,
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "dedicated",
                    "showReuseMessage": True,
                    "clear": False,
                },
            },
            {
                "label": "RAGPipe: Watch",
                "type": "shell",
                "command": "ragpipe",
                "args": ["watch", "."],
                "problemMatcher": [],
                "isBackground": True,
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": False,
                    "panel": "dedicated",
                    "showReuseMessage": True,
                    "clear": False,
                },
            },
        ],
        "inputs": [
            {
                "id": "ragpipePrompt",
                "type": "promptString",
                "description": "RAGPipe query prompt",
            }
        ],
    }

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        existing = json.loads(dest.read_text(encoding="utf-8"))
        existing_tasks = existing.get("tasks", [])
        ragpipe_labels = {t["label"] for t in tasks["tasks"]}
        filtered = [t for t in existing_tasks if t.get("label") not in ragpipe_labels]
        tasks["tasks"] = filtered + tasks["tasks"]
        existing_inputs = existing.get("inputs", [])
        existing_input_ids = {i["id"] for i in existing_inputs}
        for inp in tasks.get("inputs", []):
            if inp["id"] not in existing_input_ids:
                existing_inputs.append(inp)
        tasks["inputs"] = existing_inputs
        tasks.update({k: v for k, v in existing.items() if k not in ("tasks", "inputs")})

    dest.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote VSCode tasks to %s", dest)
    return dest


def generate_settings(
    project_path: str = ".vscode/settings.json",
    port: int = 7642,
) -> Path:
    dest = Path(project_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    settings: dict[str, Any] = {}
    if dest.exists():
        try:
            settings = json.loads(dest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Existing settings.json is not valid JSON — starting fresh.")

    settings.setdefault("ragpipe.serverPort", port)
    settings.setdefault("ragpipe.autoIndex", True)

    env = settings.setdefault("terminal.integrated.env", {})
    if isinstance(env, dict):
        env.setdefault("osx", {}).setdefault("RAGPIPE_PORT", str(port))
        env.setdefault("linux", {}).setdefault("RAGPIPE_PORT", str(port))
        env.setdefault("windows", {}).setdefault("RAGPIPE_PORT", str(port))

    dest.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote VSCode settings to %s", dest)
    return dest
