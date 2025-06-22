import websockets
from shared.server_settings import server_settings

print("PythonSponge WS server")

if server_settings.is_debug:
    print('WARNING: THIS SERVER IS RUNNING IN DEBUG MODE. THIS SHOULD ONLY HAPPEN WHEN TESTING ON LOCALHOST')
