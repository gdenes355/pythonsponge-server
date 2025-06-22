#!/usr/bin/env bash

VIRTUALENVS_DIR=/home/pythonsponge/.virtualenvs
SOURCES_DIR=/home/pythonsponge/deployed

if [ "$1" = "--silent" ]; then
	cd "$SOURCES_DIR/server" \
	  && source "$VIRTUALENVS_DIR/py_server/bin/activate" \
	  && git clean -f \
	  && git pull \
	  && pip install -r requirements.txt \
	  && sudo systemctl restart "fast_api_server" \
	  && sudo systemctl restart "ws_server"
	echo "Finished"
else
	cd "$SOURCES_DIR/server" \
	  && source "$VIRTUALENVS_DIR/py_server/bin/activate" \
	  && git clean -f \
	  && git pull \
	  && pip install -r requirements.txt \
	  && sudo systemctl restart "fast_api_server" \
	  && sudo systemctl restart "ws_server" \
	  && journalctl -u "fast_api_server.service" -f
fi


