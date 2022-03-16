import json
import logging
from paramiko import WarningPolicy
from paramiko import SSHClient
from multiprocessing import Pool

_LOGGER = logging.getLogger("unifi_tracker")

class UnifiTrackerException(Exception):
    '''General exception indicating client diff could not be processed.'''
    def __init__(self, message: str):
        super().__init__(message)

class UnifiTracker():
    def __init__(self, useHostKeys=False):
        # SSH client ignoring existing host key.
        self.ssh_client = SSHClient()
        self._useHostKeys = useHostKeys
        # Unifi command to remotely call via SSH.
        self.UNIFI_CMDLINE = 'mca-dump'
        # Properties to extract from returned JSON.
        self.UNIFI_SSID_TABLE = 'vap_table'
        self.UNIFI_CLIENT_TABLE = 'sta_table'
        # Some reasonable limit to number of hosts to scan in parallel.
        self.MAX_AP_HOST_SCANS = 32

    @property
    def UseHostKeys(self):
        return self._useHostKeys

    @UseHostKeys.setter
    def UseHostKeys(self, value):
        self._useHostKeys = value

    def exec_ssh_cmdline(self, user: str, host: str, cmdline: str):
        '''Remotely execute command via SSH'''
        try:
            if self._useHostKeys:
                _LOGGER.debug("Using system host keys file.")
                self.ssh_client.load_system_host_keys()
            else:
                self.ssh_client.set_missing_host_key_policy(WarningPolicy)
            self.ssh_client.connect(hostname=host, username=user, look_for_keys=True)
            _, stdout, stderr = self.ssh_client.exec_command(cmdline)
            out = stdout.read()
            err = stderr.read()
        finally:
            self.ssh_client.close()
        return (out, err)

    def get_ap_clients(self, ssh_username: str, ap_host: str):
        '''Retrieve clients from a Unifi AP'''
        ap_clients = []
        out, err = self.exec_ssh_cmdline(user=ssh_username, host=ap_host, cmdline=self.UNIFI_CMDLINE)
        jresult = json.loads(out.decode('utf-8'))
        if not jresult or self.UNIFI_SSID_TABLE not in jresult:
            _LOGGER.debug(f"{err}")
            raise UnifiTrackerException(f"No results for AP address {ap_host}")
        for ssid in jresult[self.UNIFI_SSID_TABLE]:
            if self.UNIFI_CLIENT_TABLE not in ssid:
                _LOGGER.debug(jresult)
                raise UnifiTrackerException(f"No client table {ap_host}")
            ap_clients += ssid.get(self.UNIFI_CLIENT_TABLE)
        return ap_clients

    def get_ap_mac_clients(self, ssh_username: str, ap_host: str):
        '''MAC to client JSON from a Unifi AP'''
        return {client.get('mac').upper(): client for client in self.get_ap_clients(ssh_username=ssh_username, ap_host=ap_host)}

    def scan_aps(self, ssh_username: str, ap_hosts: list[str], last_mac_clients: dict={}):
        '''Retrieve and merge clients from all APs; diff with last retrieved.
        Return tuple: dict of clients, list of client adds, list of client deletes.
        All AP retrievals need to succeed in order to process diff.'''
        _LOGGER.debug("scanning start")
        if len(ap_hosts) > self.MAX_AP_HOST_SCANS:
            raise UnifiTrackerException(f"Exceeded limit of {self.MAX_AP_HOST_SCANS} APs that can be scanned in parallel.")
        mac_clients = {}
        added = []
        deleted = []
        with Pool() as pool:
            for ap_mac_clients in pool.starmap(self.get_ap_mac_clients, [(ssh_username, ap_host) for ap_host in ap_hosts]):
                mac_clients.update(ap_mac_clients)
        for mac, client in mac_clients.items():
            if mac not in last_mac_clients:
                added.append(mac)
                hostname = f"{client['hostname']} ({mac})" if 'hostname' in client else mac
                _LOGGER.info(f"added {hostname}")
        for mac, client in last_mac_clients.items():
            if mac not in mac_clients:
                deleted.append(mac)
                hostname = f"{client['hostname']} ({mac})" if 'hostname' in client else mac
                _LOGGER.info(f"removed {hostname}")
        _LOGGER.debug("scanning end")

        return mac_clients, added, deleted
