import os
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
    '''Retrieve AP WiFi clients'''
    def __init__(self, useHostKeys: bool=False):
        '''Initialize with option useHostKeys property.'''
        self.ssh_client = SSHClient()
        # SSH client ignoring existing host key.
        self._useHostKeys = useHostKeys
        # SSH client connect timeout in seconds.
        self._sshTimeout = None
        # WiFi client idle time threshold in seconds.
        self._maxIdleTime = None
        # Unifi command to remotely call via SSH.
        self.UNIFI_CMDLINE = 'mca-dump'
        # Properties to extract from returned JSON.
        self.UNIFI_SSID_TABLE = 'vap_table'
        self.UNIFI_CLIENT_TABLE = 'sta_table'
        # Some reasonable limit to number of hosts to scan in parallel.
        self.MAX_AP_HOST_SCANS = 32
        # Scanning processes run in parallel; set to 0 to run serially.
        self._processes = os.cpu_count()

    @property
    def UseHostKeys(self):
        '''Whether to ignore existing SSH client host key.'''
        return self._useHostKeys

    @UseHostKeys.setter
    def UseHostKeys(self, value: bool):
        self._useHostKeys = value

    @property
    def SshTimeout(self):
        '''SSH client connect timeout in seconds.'''
        return self._sshTimeout

    @SshTimeout.setter
    def SshTimeout(self, value: float):
        self._sshTimeout = value

    @property
    def MaxIdleTime(self):
        '''WiFi client idle time threshold in seconds.'''
        return self._maxIdleTime

    @MaxIdleTime.setter
    def MaxIdleTime(self, value: int):
        self._maxIdleTime = value

    @property
    def Processes(self):
        '''Scanning processes run in parallel; set to 0 for sequential processing.'''
        return self._processes

    @Processes.setter
    def Processes(self, value: int):
        self._processes = value

    def exec_ssh_cmdline(self, user: str, host: str, cmdline: str):
        '''Remotely execute command via SSH'''
        try:
            if self._useHostKeys:
                _LOGGER.debug("Using system host keys file.")
                self.ssh_client.load_system_host_keys()
            else:
                self.ssh_client.set_missing_host_key_policy(WarningPolicy)
            self.ssh_client.connect(hostname=host,
                                    username=user,
                                    look_for_keys=True,
                                    timeout=self._sshTimeout)
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
        _LOGGER.debug(f'Scanning {ap_host}.')
        return {client.get('mac').upper(): client for client in self.get_ap_clients(ssh_username=ssh_username, ap_host=ap_host)}

    def parallel_scan(self, ssh_username: str, ap_hosts: list[str]):
        '''List of results of parallel calls to get_ap_mac_clients.'''
        with Pool(processes=self._processes) as pool:
            _LOGGER.debug(f'Running {self._processes} scans in parallel.')
            return pool.starmap(self.get_ap_mac_clients, [(ssh_username, ap_host) for ap_host in ap_hosts])

    def sequential_scan(self, ssh_username: str, ap_hosts: list[str]):
        '''List of results of sequential calls to get_ap_mac_clients'''
        all_ap_mac_clients = []
        for ap_host in ap_hosts:
            macs_res = self.get_ap_mac_clients(ssh_username, ap_host)
            all_ap_mac_clients.append(macs_res)
        return all_ap_mac_clients

    def scan_aps(self, ssh_username: str, ap_hosts: list[str], last_mac_clients: dict={}):
        '''Retrieve and merge clients from all APs; diff with last retrieved.
        Return tuple: dict of clients, list of client adds, list of client deletes.
        All AP retrievals need to succeed in order to process diff.
        '''
        _LOGGER.debug("scanning start")
        if len(ap_hosts) > self.MAX_AP_HOST_SCANS:
            raise UnifiTrackerException(f"Exceeded limit of {self.MAX_AP_HOST_SCANS} APs that can be scanned in parallel.")
        mac_clients = {}
        added = []
        deleted = []
        if self._processes == 0:
            all_ap_mac_clients = self.sequential_scan(ssh_username, ap_hosts)
        else:
            all_ap_mac_clients = self.parallel_scan(ssh_username, ap_hosts)
        for ap_mac_clients in all_ap_mac_clients:
            if self._maxIdleTime is None:
                mac_clients.update(ap_mac_clients)
            else:
                # Filter on clients below idle time threshold
                for mac, client in ap_mac_clients.items():
                    idletime = client["idletime"] if 'idletime' in client else 0
                    _LOGGER.debug(f'{mac} idletime={idletime}')
                    if idletime > self._maxIdleTime:
                        if mac in last_mac_clients:
                            _LOGGER.info(f'{mac} exceeded idle time threshold; excluding.')
                        continue
                    mac_clients[mac] = client
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
