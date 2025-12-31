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

# === Show config summary and ask for confirmation ===
echo ""
echo "📋 Current configuration:"
echo "   SERVICE_USER:   $SERVICE_USER"
echo "   AUTH_PROVIDER:  $AUTH_PROVIDER"
echo "   SERVER_NAME:    $SERVER_NAME"
echo ""

read -p "❓ Does this look correct? Type 'y' to continue: " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "❌ Aborting setup. Please review your configuration."
    exit 1
fi


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
sudo apt install -y git python3 python3-pip python3-venv nginx certbot python3-certbot-nginx unzip zip

echo -n "🐍 Python version: "
python3 --version

echo -n "📦 pip version: "
pip3 --version

echo -n "🔧 Git version: "
git --version

echo -n "🌐 Nginx version: "
/usr/sbin/nginx -v 2>&1

echo -n "🌐 Certbot version: "
sudo certbot --version

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

sudo -u "$SERVICE_USER" bash <<EOF
set -e

DEPLOYED_DIR="/home/$SERVICE_USER/deployed"
REPO_URL="$REPO_URL"
SERVER_NAME="$SERVER_NAME"
AUTH_PROVIDER="$AUTH_PROVIDER"

echo "👤 Current user: \$(whoami)"
echo "📂 DEPLOYED_DIR = \$DEPLOYED_DIR"

echo "📁 Creating folder structure..."
mkdir -p "\$DEPLOYED_DIR/app" "\$DEPLOYED_DIR/env" "\$DEPLOYED_DIR/server"

echo "ensuring correct permissions"
chmod go+x ~
chmod go-x "\$DEPLOYED_DIR/env" 

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
EOF

echo "🧪 Running finalise_env.py interactively..."

sudo -i -u "$SERVICE_USER" bash -c "source /home/$SERVICE_USER/deployed/server/.venv/bin/activate && \
    python3 /home/$SERVICE_USER/deployed/server/tools/finalise_env.py '$SERVER_NAME' '/home/$SERVICE_USER/deployed' '$AUTH_PROVIDER'"

echo "📝 Ensuring certificates via let's encrypt and certbot"
sudo certbot --nginx -d $SERVER_NAME
sudo systemctl status certbot.timer

# === Restart Nginx ===
echo "🌐 Restarting Nginx with new configs..."
sudo systemctl enable nginx
sudo /home/$SERVICE_USER/deployed/server/tools/restart-nginx.sh
echo -n "✅ Nginx status: "
systemctl is-active nginx

echo "Creating services"
# API server
if [ -f "/home/$SERVICE_USER/deployed/server/config/services/fast_api_server.service" ]; then
    echo "🔧 Installing fast_api_server.service..."
    sudo cp "/home/$SERVICE_USER/deployed/server/config/services/fast_api_server.service" /etc/systemd/system/fast_api_server.service
else
    echo "⚠️  Warning: fast_api_server.service not found in expected location."
fi

# WebSocket server
if [ -f "/home/$SERVICE_USER/deployed/server/config/services/ws_server.service" ]; then
    echo "🔧 Installing ws_server.service..."
    sudo cp "/home/$SERVICE_USER/deployed/server/config/services/ws_server.service" /etc/systemd/system/ws_server.service
else
    echo "⚠️  Warning: ws_server.service not found in expected location."
fi

echo "🔧 Granting passwordless sudo access to restart services for $SERVICE_USER..."
SUDOERS_FILE="/etc/sudoers.d/pythonsponge-restarts"

if [ ! -f "$SUDOERS_FILE" ]; then
    echo "🔧 Granting passwordless sudo access to restart services for $SERVICE_USER..."
    echo "$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart fast_api_server.service, /bin/systemctl restart ws_server.service" | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 440 "$SUDOERS_FILE"
else
    echo "✅ Sudoers file already exists at $SUDOERS_FILE. Skipping."
fi

systemctl daemon-reload

# === Create symbolic link for management tool ===
echo "🛠️  Creating pythonsponge management command..."

LINK_NAME="/usr/local/bin/pythonsponge"
TARGET_SCRIPT="/home/$SERVICE_USER/deployed/server/tools/pythonsponge.sh"

if [ -L "$LINK_NAME" ]; then
    if [ "$(readlink "$LINK_NAME")" = "$TARGET_SCRIPT" ]; then
        echo "🔗 Symbolic link '$LINK_NAME' already exists and is correct. Skipping."
    else
        echo "♻️ Updating existing symbolic link '$LINK_NAME'..."
        sudo ln -sf "$TARGET_SCRIPT" "$LINK_NAME"
    fi
elif [ -e "$LINK_NAME" ]; then
    echo "❌ File '$LINK_NAME' exists and is not a symbolic link. Not overwriting."
else
    echo "🔗 Creating symbolic link '$LINK_NAME' -> '$TARGET_SCRIPT'"
    sudo ln -s "$TARGET_SCRIPT" "$LINK_NAME"
fi


echo "🎉 PythonSponge server setup complete!"
