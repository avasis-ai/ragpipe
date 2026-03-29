from ragpipe.integrations.indexer import index_project, detect_project_type
from ragpipe.integrations.watcher import watch
from ragpipe.integrations.server import serve
from ragpipe.integrations.git_hooks import install_hook, remove_hook, list_hooks
from ragpipe.integrations.vscode import generate_tasks, generate_settings

__all__ = [
    "index_project",
    "detect_project_type",
    "watch",
    "serve",
    "install_hook",
    "remove_hook",
    "list_hooks",
    "generate_tasks",
    "generate_settings",
]
