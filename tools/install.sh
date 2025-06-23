#!/bin/bash

set -e  # Exit on error

CONFIG_FILE="pythonsponge-config.env"

# === Ensure config file is present ===
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_URL="https://raw.githubusercontent.com/gdenes355/pythonsponge-server/main/config/install/$CONFIG_FILE"
    echo "📄 Configuration file '$CONFIG_FILE' not found."
    echo "🌐 Downloading from $CONFIG_URL..."
    curl -fsSL "$CONFIG_URL" -o "$CONFIG_FILE"
    echo "✅ '$CONFIG_FILE' downloaded."
    echo "🛠️  Please open and edit '$CONFIG_FILE' to complete your setup."
    echo "Install.sh is quitting for now. Rerun once the config is completed"
    exit 0
fi

# === CONFIGURATION ===
REPO_URL="https://github.com/gdenes355/pythonsponge-server.git"


# === Load config values into environment ===
echo "🔄 Loading configuration from '$CONFIG_FILE'..."
set -a
. "./$CONFIG_FILE"
set +a

# 1. Check SERVICE_USER is set and not empty
if [ -z "$SERVICE_USER" ]; then
  echo "❌ Error: SERVICE_USER is not set."
  exit 1
fi

# 2. Check AUTH_PROVIDER is set and not empty
if [ -z "$AUTH_PROVIDER" ]; then
  echo "❌ Error: AUTH_PROVIDER is not set."
  exit 1
fi

# 3. Check SERVER_NAME is not blank or 'localhost'
if [ -z "$SERVER_NAME" ] || [ "$SERVER_NAME" = "localhost" ]; then
  echo "❌ Error: SERVER_NAME must be set and cannot be 'localhost'."
  exit 1
fi

echo "✅ Environment checks passed."


echo "🛠️  Initializing PythonSponge VM setup for user '$SERVICE_USER'..."

# === Create service user ===
if id "$SERVICE_USER" &>/dev/null; then
    echo "✅ User '$SERVICE_USER' already exists. Skipping creation."
else
    echo "➕ Creating user '$SERVICE_USER'..."
    sudo adduser --disabled-password --gecos "" "$SERVICE_USER"
fi

# === Install system packages ===
echo "⬇️ Installing required packages..."
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv nginx

echo -n "🐍 Python version: "
python3 --version

echo -n "📦 pip version: "
pip3 --version

echo -n "🔧 Git version: "
git --version

echo -n "🌐 Nginx version: "
nginx -v 2>&1

# === Limit systemd journal log size ===
echo "📝 Limiting systemd journal log size..."

JOURNALD_CONF="/etc/systemd/journald.conf"

sudo sed -i 's/^#*SystemMaxUse=.*/SystemMaxUse=1K/' "$JOURNALD_CONF"
sudo sed -i 's/^#*SystemMaxFileSize=.*/SystemMaxFileSize=1K/' "$JOURNALD_CONF"

grep -q '^SystemMaxUse=' "$JOURNALD_CONF" || echo 'SystemMaxUse=1K' | sudo tee -a "$JOURNALD_CONF" > /dev/null
grep -q '^SystemMaxFileSize=' "$JOURNALD_CONF" || echo 'SystemMaxFileSize=1K' | sudo tee -a "$JOURNALD_CONF" > /dev/null

echo "🔁 Restarting systemd-journald..."
sudo systemctl restart systemd-journald
echo "✅ systemd journal log size limited."

# === Enable and start Nginx ===
echo "🌐 Enabling and starting Nginx..."
sudo systemctl enable nginx
sudo systemctl start nginx
echo -n "✅ Nginx status: "
systemctl is-active nginx

# === Allow Nginx ports through UFW if available ===
if command -v ufw &>/dev/null; then
    echo "🛡️  Allowing Nginx through UFW..."
    sudo ufw allow 'Nginx HTTP'
    sudo ufw allow 'Nginx HTTPS'
else
    echo "⚠️  UFW not found. Skipping firewall rule setup."
fi



# === Main setup as service user ===
echo "👤 Switching to '$SERVICE_USER' for application setup..."

sudo -u "$SERVICE_USER" bash -c <<EOF
set -e

DEPLOYED_DIR="/home/$SERVICE_USER/deployed"
REPO_URL="$REPO_URL"
SERVER_NAME="$SERVER_NAME"
AUTH_PROVIDER="$AUTH_PROVIDER"

echo "👤 Current user: \$(whoami)"
echo "📂 DEPLOYED_DIR = \$DEPLOYED_DIR"

echo "📁 Creating folder structure..."
mkdir -p "\$DEPLOYED_DIR/app" "\$DEPLOYED_DIR/env" "\$DEPLOYED_DIR/server"

echo "🔄 Cloning repository or pulling latest changes..."
if [ ! -d "\$DEPLOYED_DIR/server/.git" ]; then
    echo "📦 Cloning repository..."
    git clone "\$REPO_URL" "\$DEPLOYED_DIR/server"
    echo "⚙️  Configuring Git to avoid rebase on pull..."
    git -C "\$DEPLOYED_DIR/server" config pull.rebase false
else
    echo "✅ Repository already exists. Pulling latest changes..."
    git -C "\$DEPLOYED_DIR/server" pull
fi

VENV_DIR="\$DEPLOYED_DIR/server/.venv"
echo "🐍 Creating virtual environment \$VENV_DIR..."
if [ ! -d "\$VENV_DIR" ]; then
    echo "📁 Creating new virtual environment at \$VENV_DIR"
    python3 -m venv "\$VENV_DIR"
    echo "✅ Virtual environment created."
else
    echo "ℹ️ Virtual environment already exists. Skipping creation."
fi

echo "✅ Activating virtual environment and installing dependencies..."
source "\$VENV_DIR/bin/activate"

cd "\$DEPLOYED_DIR/server"
if [ -f requirements.txt ]; then
    pip install --no-cache-dir -r requirements.txt
    echo "✅ Dependencies installed."
else
    echo "⚠️ requirements.txt not found. Skipping."
fi

python3 tools/finalise_env.py "\$SERVER_NAME" "\$DEPLOYED_DIR" "\$AUTH_PROVIDER"

echo "🎉 PythonSponge server setup complete!"
EOF

