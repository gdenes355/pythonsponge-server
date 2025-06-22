#! /bin/bash


VIRTUALENVS_DIR=/home/pythonsponge/.virtualenvs
SERVER_DIR=/home/pythonsponge/deployed/server
ENV_FILES_DIR=/home/pythonsponge/deployed/env


function export_env_vars {
    set -a  # Mark variables which are modified or created for export.
    source "$1"
    set +a
}


echo "STARTING websocket_server" \
      && source "$VIRTUALENVS_DIR/py_server/bin/activate" \
      && cd "$SERVER_DIR" \
      && export_env_vars "$ENV_FILES_DIR/.env" \
      && python -m ws_server.main
