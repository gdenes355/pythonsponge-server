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
VENVWRAPPER_PROFILE="/etc/profile.d/virtualenvwrapper.sh"


# === Load config values into environment ===
echo "🔄 Loading configuration from '$CONFIG_FILE'..."
set -a
. "./$CONFIG_FILE"
set +a


echo "🛠️  Initializing PythonSponge VM setup for user '$SERVICE_USER'..."

# === CONFIGURATION ===
USER_HOME="/home/$SERVICE_USER"
DEPLOYED_DIR="$USER_HOME/deployed"

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

# === Install virtualenvwrapper globally ===
echo "📦 Installing virtualenvwrapper (with --break-system-packages)..."
sudo pip3 install --break-system-packages virtualenvwrapper

echo -n "🧰 virtualenvwrapper installed at: "
which virtualenvwrapper.sh

# === Configure global virtualenvwrapper environment ===
if [ ! -f "$VENVWRAPPER_PROFILE" ]; then
    echo "⚙️ Writing global virtualenvwrapper configuration to $VENVWRAPPER_PROFILE..."
    sudo tee "$VENVWRAPPER_PROFILE" > /dev/null <<EOF
# Global virtualenvwrapper setup — uses $SERVICE_USER's environment
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
export WORKON_HOME=$USER_HOME/.virtualenvs
export PROJECT_HOME=$DEPLOYED_DIR
source /usr/local/bin/virtualenvwrapper.sh
EOF
    echo "✅ Global virtualenvwrapper config written."
else
    echo "ℹ️ Global virtualenvwrapper config already exists. Skipping."
fi

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

env USER_HOME="/home/$SERVICE_USER" \
    PROJECT_HOME="/home/$SERVICE_USER/deployed" \
    REPO_URL="$REPO_URL" \
    sudo -u "$SERVICE_USER" bash <<'EOF'
set -e

echo "👤 Current user: $(whoami)"

WORKON_HOME="$USER_HOME/.virtualenvs"

echo "📁 Creating folder structure..."
mkdir -p "$PROJECT_HOME/app" "$PROJECT_HOME/env" "$PROJECT_HOME/server"

echo "🔄 Cloning repository or pulling latest changes..."
if [ ! -d "$PROJECT_HOME/server/.git" ]; then
    echo "📦 Cloning repository..."
    git clone "$REPO_URL" "$PROJECT_HOME/server"
    echo "⚙️  Configuring Git to avoid rebase on pull..."
    git -C "$PROJECT_HOME/server" config pull.rebase false
else
    echo "✅ Repository already exists. Pulling latest changes..."
    git -C "$PROJECT_HOME/server" pull
fi

echo "🐍 Creating virtual environment 'py_server'..."
export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
export WORKON_HOME="$WORKON_HOME"
export PROJECT_HOME="$PROJECT_HOME"
source /usr/local/bin/virtualenvwrapper.sh

if [ ! -d "$WORKON_HOME/py_server" ]; then
    mkvirtualenv -p python3 -a "$PROJECT_HOME/server" py_server
    echo "✅ Virtualenv 'py_server' created."
else
    echo "ℹ️ Virtualenv 'py_server' already exists. Skipping."
fi

echo "✅ Activating environment and installing requirements..."
workon py_server

cd "$PROJECT_HOME/server"
if [ -f requirements.txt ]; then
    pip install --no-cache-dir -r requirements.txt
    echo "✅ Dependencies installed."
else
    echo "⚠️ requirements.txt not found. Skipping."
fi

python3 tools/finalise_env.py "$SERVER_NAME" "$PROJECT_HOME"

echo "🎉 PythonSponge server setup complete!"
EOF
