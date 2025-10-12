import os

from shared.admin_list import ADMINS
from shared.models import ServerSettings, AuthProvider


# add admin/teacher email addresses here


def _load_settings_from_env() -> ServerSettings:
    server_name = os.getenv('SERVER_NAME', None)
    site_url = f"https://{server_name}" if server_name else 'http://localhost:3000'
    ws_url = f"wss://{server_name}/ws/" if server_name else 'ws://localhost:5002'
    return ServerSettings(
        is_debug=os.getenv('DEBUG', 'False').lower() in ('true', '1', 't'),
        auth_provider=AuthProvider(os.getenv('AUTH_PROVIDER', AuthProvider.MSAL)) if os.getenv('AUTH_PROVIDER', None) else None,
        google_client_id=os.getenv('GOOGLE_AUTH_CLIENT_ID', None),
        msal_client_id=os.getenv('MSAL_CLIENT_ID', None),
        msal_tenant_id=os.getenv('MSAL_TENANT_ID', None),
        utils_pwd=os.getenv('UTILS_PW', None),
        jwt_sercret_key=os.getenv('JWT_SECRET_KEY'),
        admin_accounts=ADMINS.copy(),
        server_dir = os.path.normpath(f'{os.getcwd()}'),
        fernet_key=os.getenv('ENC_KEY'),
        site_url=site_url,
        ws_url=ws_url,
        can_edit_books_folder=os.getenv('CAN_EDIT_BOOKS_FOLDER', 'False').lower() in ('true', '1', 't'),
    )

server_settings = _load_settings_from_env()
