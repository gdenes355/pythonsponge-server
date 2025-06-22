#!/usr/bin/env python3

"""
Python script to finalise the server's env setup

This is called within install.sh once Python and the folder structure have been set up correctly.

Usage: python3 setup_env.py [server_name] [deployed_folder]
"""

import sys
import secrets
import string
from pathlib import Path
from cryptography.fernet import Fernet

def generate_fernet_key():
    return Fernet.generate_key().decode()

def generate_jwt_secret(length=24):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 setup_env.py [server_name] [deployed_folder]")
        sys.exit(1)

    server_name = sys.argv[1]
    deployed_folder = Path(sys.argv[2]).resolve()
    env_path = deployed_folder / "env" / ".env"

    if env_path.exists():
        print(f"✅ {env_path} already exists. Skipping creation.")
        return

    print(f"📝 Creating {env_path}...")

    env_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# Environment for {server_name}
DEBUG=False
ENC_KEY={generate_fernet_key()}
JWT_SECRET_KEY={generate_jwt_secret()}
SERVER_NAME={server_name}
"""

    with env_path.open("w") as f:
        f.write(content)

    print(f"✅ {env_path} created successfully.")

if __name__ == "__main__":
    main()
