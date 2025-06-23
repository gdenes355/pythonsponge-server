#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_help() {
    echo "Usage: $0 [command]"
    echo
    echo "Available commands:"
    echo "  redeploy            Pulls latest server code and restarts the Python server"
    echo "  restart-nginx       Updates nginx config and restarts nginx"
    echo "  redeploy-frontend   Redeploys the frontend (React)"
    echo "  rerun-install       Downloads and reruns the full install script"
    echo "  --help              Show this help message"
}

case "$1" in
    redeploy)
        sudo "$SCRIPT_DIR/redeploy.sh"
        ;;
    restart-nginx)
        sudo "$SCRIPT_DIR/restart-nginx.sh"
        ;;
    redeploy-frontend)
        sudo "$SCRIPT_DIR/redeploy-frontend.sh"
        ;;
    rerun-install)
        cd ~
        curl -fsSL https://raw.githubusercontent.com/gdenes355/pythonsponge-server/main/tools/install.sh -o install.sh
        chmod +x install.sh
        sudo ./install.sh
        ;;
    --help | -h)
        print_help
        ;;
    *)
        echo "❌ Unknown command: '$1'"
        echo
        print_help
        exit 1
        ;;
esac
