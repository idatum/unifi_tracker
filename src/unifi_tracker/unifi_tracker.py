import json
import logging
from paramiko import WarningPolicy
from paramiko import SSHClient
from multiprocessing import Pool

_LOGGER = logging.getLogger("unifi_tracker")
SSH_CLIENT = SSHClient()
SSH_CLIENT.set_missing_host_key_policy(WarningPolicy)
UNIFI_CMDLINE = 'mca-dump'
UNIFI_SSID_TABLE = 'vap_table'
UNIFI_CLIENT_TABLE = 'sta_table'
# Some reasonable limit to number of hosts to scan in parallel.
MAX_AP_HOST_SCANS = 32

class UnifiTrackerException(Exception):
    '''General exception indicating client diff could not be processed.'''
    def __init__(self, message: str):
        super().__init__(message)


def exec_ssh_cmdline(user: str, host: str, cmdline: str):
    '''Remotely execute command via SSH'''
    try:
        SSH_CLIENT.connect(hostname=host, username=user, look_for_keys=True)
        _, stdout, stderr = SSH_CLIENT.exec_command(cmdline)
        out = stdout.read()
        err = stderr.read()
    finally:
        SSH_CLIENT.close()
    return (out, err)


def get_ap_clients(ssh_username: str, ap_host: str):
    '''Retrieve clients from a Unifi AP'''
    ap_clients = []
    out, err = exec_ssh_cmdline(user=ssh_username, host=ap_host, cmdline=UNIFI_CMDLINE)
    jresult = json.loads(out.decode('utf-8'))
    if not jresult or UNIFI_SSID_TABLE not in jresult:
        _LOGGER.debug(f"{err}")
        raise UnifiTrackerException(f"No results for AP address {ap_host}")
    for ssid in jresult[UNIFI_SSID_TABLE]:
        if UNIFI_CLIENT_TABLE not in ssid:
            _LOGGER.debug(jresult)
            raise UnifiTrackerException(f"No client table {ap_host}")
        ap_clients += ssid.get(UNIFI_CLIENT_TABLE)
    return ap_clients


def get_ap_mac_clients(ssh_username: str, ap_host: str):
    '''MAC to client JSON from a Unifi AP'''
    return {client.get('mac').upper(): client for client in get_ap_clients(ssh_username=ssh_username, ap_host=ap_host)}


def scan_aps(ssh_username: str, ap_hosts: list[str], last_mac_clients: dict={}):
    '''Retrieve and merge clients from all APs; diff with last retrieved.
    Return tuple of dict of clients, list of client adds, list of client deletes.
    All AP retrievals need to succeed in order to process diff.'''
    _LOGGER.debug("scanning start")
    if len(ap_hosts) > MAX_AP_HOST_SCANS:
        raise UnifiTrackerException(f"Exceeded limit of {MAX_AP_HOST_SCANS} APs that can be scanned in parallel.")
    mac_clients = {}
    added = []
    deleted = []
    with Pool() as pool:
        for ap_mac_clients in pool.starmap(get_ap_mac_clients, [(ssh_username, ap_host) for ap_host in ap_hosts]):
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
