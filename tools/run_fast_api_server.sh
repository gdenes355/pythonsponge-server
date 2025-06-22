#! /bin/bash


VIRTUALENVS_DIR=/home/pythonsponge/.virtualenvs
SERVER_DIR=/home/pythonsponge/deployed/server
ENV_FILES_DIR=/home/pythonsponge/deployed/env


function export_env_vars {
    set -a  # Mark variables which are modified or created for export.
    source "$1"
    set +a
}


echo "STARTING fastapi server" \
      && source "$VIRTUALENVS_DIR/py_server/bin/activate" \
      && cd "$SERVER_DIR" \
      && export_env_vars "$ENV_FILES_DIR/.env" \
      && uvicorn fast_api_server.main:app --host 0.0.0.0 --port 8000 --workers 4
