import os
from shared.models import ServerSettings, AuthProvider

def _load_settings_from_env() -> ServerSettings:
    return ServerSettings(
        is_debug=os.getenv('DEBUG', 'False').lower() in ('true', '1', 't'),
        auth_provider=AuthProvider(os.getenv('AUTH_PROVIDER', None)) if os.getenv('AUTH_PROVIDER', None) else None,
        google_client_id=os.getenv('GOOGLE_AUTH_CLIENT_ID', None),
        utils_pwd=os.getenv('UTILS_PW', None),
    )

server_settings = _load_settings_from_env()
