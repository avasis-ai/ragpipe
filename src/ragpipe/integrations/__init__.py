def __getattr__(name):
    _lazy = {
        "index_project": "ragpipe.integrations.indexer",
        "detect_project_type": "ragpipe.integrations.indexer",
        "watch": "ragpipe.integrations.watcher",
        "serve": "ragpipe.integrations.server",
        "install_hook": "ragpipe.integrations.git_hooks",
        "remove_hook": "ragpipe.integrations.git_hooks",
        "list_hooks": "ragpipe.integrations.git_hooks",
        "generate_tasks": "ragpipe.integrations.vscode",
        "generate_settings": "ragpipe.integrations.vscode",
    }
    if name in _lazy:
        import importlib

        mod = importlib.import_module(_lazy[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
