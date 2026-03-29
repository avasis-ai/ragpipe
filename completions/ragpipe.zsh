#compdef ragpipe

_ragpipe() {
    local -a commands
    commands=(
        'init:Create a starter pipeline.yaml'
        'run:Execute a pipeline YAML config'
        'ingest:Ingest data from any source'
        'query:Search your ingested data'
        'index:Smart-index a codebase'
        'watch:Watch a directory and auto-reindex'
        'serve:Start local API server'
        'search:Search with optional fzf'
        'git:Manage git hooks'
        'vscode:Generate VSCode config'
        'macos:macOS-specific integrations'
        'linux:Linux-specific integrations'
    )

    if (( CURRENT == 2 )); then
        _describe 'command' commands
        return
    fi

    case "${words[2]}" in
        ingest)
            _arguments \
                '--sink[Target sink: json, qdrant, pinecone]:sink:(json qdrant pinecone)' \
                '--sink-path[Output path for JSON sink]:path:_files' \
                '--chunk-size[Chunk size]:size:' \
                '--overlap[Chunk overlap]:size:' \
                '--embed[Generate embeddings]' \
                '--collection[Vector DB collection name]:name:' \
                '--clean[Clean HTML]' \
                '--no-clean[Skip HTML cleaning]' \
                '--pii[Remove PII]' \
                '*:path:_files'
            ;;
        query)
            _arguments \
                '--sink[Data sink]:sink:(json qdrant)' \
                '--sink-path[Path for JSON sink]:path:_files' \
                '--top-k[Number of results]:n:' \
                '--mode[Search mode]:mode:(auto semantic keyword)' \
                '*:query text'
            ;;
        index)
            _arguments \
                '--sink[Target sink]:sink:(json qdrant)' \
                '--sink-path[Output path]:path:_files' \
                '--chunk-size[Chunk size]:size:' \
                '--overlap[Chunk overlap]:size:' \
                '--embed[Generate embeddings]' \
                '--exclude[Extra ignore patterns]:pattern:' \
                '--max-file-size[Max file size in bytes]:size:' \
                '*:path:_directories'
            ;;
        watch)
            _arguments \
                '--sink-path[Output path]:path:_files' \
                '--chunk-size[Chunk size]:size:' \
                '--debounce[Debounce seconds]:seconds:' \
                '--extensions[File extensions to watch]:exts:' \
                '*:path:_directories'
            ;;
        serve)
            _arguments \
                '--data[Data file path]:path:_files' \
                '--host[Bind host]:host:' \
                '--port[Bind port]:port:' \
                '--embed[Enable embeddings]'
            ;;
        search)
            _arguments \
                '--sink-path[Data file path]:path:_files' \
                '--top-k[Results]:n:' \
                '--mode[Search mode]:mode:(auto semantic keyword)' \
                '--fzf[Use fzf for interactive search]'
            ;;
        git)
            local -a git_cmds
            git_cmds=('install:Install git hook' 'remove:Remove git hook' 'list:List installed hooks')
            if (( CURRENT == 3 )); then
                _describe 'git command' git_cmds
            fi
            ;;
        vscode)
            local -a vscode_cmds
            vscode_cmds=('tasks:Generate tasks.json' 'settings:Generate settings.json')
            if (( CURRENT == 3 )); then
                _describe 'vscode command' vscode_cmds
            fi
            ;;
        macos)
            local -a macos_cmds
            macos_cmds=('spotlight:Search via Spotlight' 'index:Index via Spotlight')
            if (( CURRENT == 3 )); then
                _describe 'macos command' macos_cmds
            fi
            ;;
        linux)
            local -a linux_cmds
            linux_cmds=('service:Generate systemd service' 'timer:Generate systemd timer' 'install:Install systemd service')
            if (( CURRENT == 3 )); then
                _describe 'linux command' linux_cmds
            fi
            ;;
    esac
}

_ragpipe
