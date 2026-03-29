complete -c ragpipe -f

complete -c ragpipe -n '__fish_use_subcommand' -a init -d 'Create starter pipeline.yaml'
complete -c ragpipe -n '__fish_use_subcommand' -a run -d 'Execute pipeline YAML'
complete -c ragpipe -n '__fish_use_subcommand' -a ingest -d 'Ingest data from any source'
complete -c ragpipe -n '__fish_use_subcommand' -a query -d 'Search ingested data'
complete -c ragpipe -n '__fish_use_subcommand' -a index -d 'Smart-index a codebase'
complete -c ragpipe -n '__fish_use_subcommand' -a watch -d 'Watch and auto-reindex'
complete -c ragpipe -n '__fish_use_subcommand' -a serve -d 'Start local API server'
complete -c ragpipe -n '__fish_use_subcommand' -a search -d 'Search with optional fzf'
complete -c ragpipe -n '__fish_use_subcommand' -a git -d 'Manage git hooks'
complete -c ragpipe -n '__fish_use_subcommand' -a vscode -d 'Generate VSCode config'
complete -c ragpipe -n '__fish_use_subcommand' -a macos -d 'macOS integrations'
complete -c ragpipe -n '__fish_use_subcommand' -a linux -d 'Linux integrations'

complete -c ragpipe -n '__fish_seen_subcommand_from ingest' -l sink -d 'Target sink'
complete -c ragpipe -n '__fish_seen_subcommand_from ingest' -l sink-path -d 'Output path'
complete -c ragpipe -n '__fish_seen_subcommand_from ingest' -l chunk-size -d 'Chunk size'
complete -c ragpipe -n '__fish_seen_subcommand_from ingest' -l embed -d 'Generate embeddings'
complete -c ragpipe -n '__fish_seen_subcommand_from ingest' -l pii -d 'Remove PII'

complete -c ragpipe -n '__fish_seen_subcommand_from query' -l sink -d 'Data sink'
complete -c ragpipe -n '__fish_seen_subcommand_from query' -l top-k -d 'Number of results'
complete -c ragpipe -n '__fish_seen_subcommand_from query' -l mode -d 'Search mode'

complete -c ragpipe -n '__fish_seen_subcommand_from index' -l sink-path -d 'Output path'
complete -c ragpipe -n '__fish_seen_subcommand_from index' -l chunk-size -d 'Chunk size'
complete -c ragpipe -n '__fish_seen_subcommand_from index' -l embed -d 'Generate embeddings'
complete -c ragpipe -n '__fish_seen_subcommand_from index' -l exclude -d 'Extra ignore patterns'

complete -c ragpipe -n '__fish_seen_subcommand_from watch' -l sink-path -d 'Output path'
complete -c ragpipe -n '__fish_seen_subcommand_from watch' -l debounce -d 'Debounce seconds'

complete -c ragpipe -n '__fish_seen_subcommand_from serve' -l data -d 'Data file path'
complete -c ragpipe -n '__fish_seen_subcommand_from serve' -l host -d 'Bind host'
complete -c ragpipe -n '__fish_seen_subcommand_from serve' -l port -d 'Bind port'

complete -c ragpipe -n '__fish_seen_subcommand_from search' -l sink-path -d 'Data file path'
complete -c ragpipe -n '__fish_seen_subcommand_from search' -l fzf -d 'Use fzf'
complete -c ragpipe -n '__fish_seen_subcommand_from search' -l top-k -d 'Results count'
