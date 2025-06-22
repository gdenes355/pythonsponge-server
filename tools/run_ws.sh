#! /bin/bash


SERVER_DIR=/home/$USER/deployed/server
ENV_FILES_DIR=/home/$USER/deployed/env


function export_env_vars {
    set -a  # Mark variables which are modified or created for export.
    source "$1"
    set +a
}


echo "STARTING websocket_server" \
    && cd "$SERVER_DIR" \
    && source ".venv/bin/activate" \
    && export_env_vars "$ENV_FILES_DIR/.env" \
    && python -m ws_server.main
