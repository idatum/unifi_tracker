import unittest
import json
import unifi_tracker as unifi

TEST_RESULT_PROLOG = b'{"vap_table": [{"sta_table": '
TEST_RESULT_EPILOG = b'}]}'
TEST_CLIENTS1 = b'[{"mac": "mac1", "hostname": "hostname1"}, {"mac": "mac2", "hostname": "hostname2"}]'
TEST_CLIENTS2 = b'[{"mac": "mac1", "hostname": "hostname1"}, {"mac": "mac3", "hostname": "hostname3"}]'
TEST_CLIENTS3 = b'[{"mac": "mac3", "hostname": "hostname3"}, {"mac": "mac1", "hostname": "hostname1"}]'


def mock1_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    return (TEST_RESULT_PROLOG + TEST_CLIENTS1 + TEST_RESULT_EPILOG, b'')


def mock2_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    return (TEST_RESULT_PROLOG + TEST_CLIENTS2 + TEST_RESULT_EPILOG, b'')


def mock3_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    return (TEST_RESULT_PROLOG + TEST_CLIENTS3 + TEST_RESULT_EPILOG, b'')


class TestDiff(unittest.TestCase):

    def test_simple_parse(self):
        unifi.exec_ssh_cmdline = mock1_exec_ssh_cmdline
        test_clients = unifi.get_ap_clients('testhost')
        assert(TEST_CLIENTS1.decode('utf-8') == json.dumps(test_clients))

    def test_diff1(self):
        unifi.exec_ssh_cmdline = mock2_exec_ssh_cmdline
        diff = unifi.scan_aps(['testhost'], json.loads((TEST_RESULT_PROLOG + TEST_CLIENTS1 + TEST_RESULT_EPILOG)))
        # Should be deterministic diff
        assert("({'MAC1': {'mac': 'mac1', 'hostname': 'hostname1'}, 'MAC3': {'mac': 'mac3', 'hostname': 'hostname3'}}, ['MAC1', 'MAC3'], ['vap_table'])" == \
               str(diff))

    def test_diff2(self):
        unifi.exec_ssh_cmdline = mock3_exec_ssh_cmdline
        diff = unifi.scan_aps(['testhost'], json.loads((TEST_RESULT_PROLOG + TEST_CLIENTS1 + TEST_RESULT_EPILOG)))
        # Should be deterministic diff
        assert("({'MAC3': {'mac': 'mac3', 'hostname': 'hostname3'}, 'MAC1': {'mac': 'mac1', 'hostname': 'hostname1'}}, ['MAC3', 'MAC1'], ['vap_table'])" == \
               str(diff))

if __name__ == "__main__":
    unittest.main()
