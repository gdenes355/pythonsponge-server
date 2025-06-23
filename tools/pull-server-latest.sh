#!/usr/bin/env bash

SOURCES_DIR=/home/pythonsponge/deployed

cd "$SOURCES_DIR/server" \
	&& source ".venv/bin/activate" \
	&& git clean -f \
	&& git pull \
	&& pip install -r requirements.txt
echo "Finished"
