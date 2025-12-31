import os
import requests
from shared.server_settings import server_settings
from shared.logging import logger

class MaintenanceService:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(MaintenanceService, cls).__new__(cls)
        return cls.instance

    def get_private_ip(self):
        # get local IP address
        hostname = os.popen('hostname -I').read().strip()
        if hostname:
            return hostname.split()[0]
        else:
            return '0.0.0.0', 400

    def get_public_ip(self):
        requests.packages.urllib3.util.connection.HAS_IPV6 = False
        response = requests.get('https://ifconfig.co/ip')
        if response.status_code != 200:
            return '0.0.0.0', 400
        else:
            return response.text.strip()

    def get_uptime(self):
        with open('/proc/uptime', 'r') as f:
            return float(f.readline().split()[0])

    def restart_ws_server(self):
        logger.info(f'Restarting ws server')
        res = os.system(f'{server_settings.server_dir}/tools/restart-ws.sh')
        logger.info(f'Restart ws server result: {res}')
        return res