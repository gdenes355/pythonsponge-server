#!/usr/bin/env bash

SOURCES_DIR=/home/pythonsponge/deployed
ENV_FILES_DIR="$SOURCES_DIR/env"
NGINX_SRC_DIR="$SOURCES_DIR/server/config/nginx/sites-available"
NGINX_DEST_DIR=/etc/nginx/sites-available
NGINX_ENABLED_DIR=/etc/nginx/sites-enabled

export_env_vars() {
    local file="$1"
    if [ -f "$file" ]; then
        export $(grep -v '^#' "$file" | xargs)
    else
        echo "❌ Environment file not found: $file"
        exit 1
    fi
}

export_env_vars "$ENV_FILES_DIR/.env"

if [ -z "$SERVER_NAME" ]; then
    echo "❌ SERVER_NAME is not set in $ENV_FILES_DIR/.env"
    exit 1
fi

echo "🧹 Cleaning existing Nginx site configs..."
sudo rm /etc/nginx/sites-available/*
sudo rm /etc/nginx/sites-enabled/*

echo "📄 Preparing new Nginx site configs..."
for file in "$NGINX_SRC_DIR"/*; do
    filename=$(basename "$file")
    envsubst '${SERVER_NAME}' < "$file" > "$NGINX_DEST_DIR/$filename"
    cp "$NGINX_DEST_DIR/$filename" "$NGINX_ENABLED_DIR/$filename"
done

sudo systemctl stop nginx
sudo systemctl start nginx
