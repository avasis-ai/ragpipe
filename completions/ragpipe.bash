_ragpipe_completion() {
    local cur prev words cword
    _init_completion || return

    case "${prev}" in
        ragpipe)
            COMPREPLY=($(compgen -W "init run ingest query index watch serve git vscode macos linux search" -- "${cur}"))
            ;;
        ingest)
            COMPREPLY=($(compgen -W "--sink --sink-path --chunk-size --overlap --embed --collection --clean --no-clean --pii --help" -- "${cur}"))
            [[ ${cur} == -* ]] || COMPREPLY+=($(compgen -f -- "${cur}"))
            ;;
        query)
            COMPREPLY=($(compgen -W "--sink --sink-path --top-k --collection --mode --help" -- "${cur}"))
            ;;
        index)
            COMPREPLY=($(compgen -W "--sink --sink-path --chunk-size --overlap --embed --exclude --max-file-size --help" -- "${cur}"))
            [[ ${cur} == -* ]] || COMPREPLY+=($(compgen -d -- "${cur}"))
            ;;
        watch)
            COMPREPLY=($(compgen -W "--sink --sink-path --chunk-size --debounce --extensions --help" -- "${cur}"))
            [[ ${cur} == -* ]] || COMPREPLY+=($(compgen -d -- "${cur}"))
            ;;
        serve)
            COMPREPLY=($(compgen -W "--data --host --port --help" -- "${cur}"))
            ;;
        run)
            [[ ${cur} == -* ]] || COMPREPLY+=($(compgen -f -- "${cur}"))
            ;;
        search)
            COMPREPLY=($(compgen -W "--sink-path --top-k --mode --fzf --help" -- "${cur}"))
            ;;
        git)
            COMPREPLY=($(compgen -W "hook install remove list --help" -- "${cur}"))
            ;;
        vscode)
            COMPREPLY=($(compgen -W "tasks settings --help" -- "${cur}"))
            ;;
        macos)
            COMPREPLY=($(compgen -W "spotlight search index --help" -- "${cur}"))
            ;;
        linux)
            COMPREPLY=($(compgen -W "service timer install --help" -- "${cur}"))
            ;;
        *)
            ;;
    esac
}

complete -F _ragpipe_completion ragpipe
