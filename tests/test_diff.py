import unittest
import json
import unifi_tracker as unifi
import mock_clients as mcl


def mock0_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    return (json.dumps({"hostname": mcl.TEST_AP,
                            "vap_table": [{"sta_table": mcl.TEST_CLIENTS0}]}).encode(), b'')


def mock1_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    return (json.dumps({"hostname": mcl.TEST_AP,
                            "vap_table": [{"sta_table": mcl.TEST_CLIENTS1}]}).encode(), b'')


def mock2_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    return (json.dumps({"hostname": mcl.TEST_AP,
                            "vap_table": [{"sta_table": mcl.TEST_CLIENTS2}]}).encode(), b'')


class TestDiff(unittest.TestCase):

    def test_simple_parse(self):
        '''Expected get_ap_clients result'''
        unifiTracker = unifi.UnifiTracker()
        # Force sequential
        unifiTracker.Processes = 0
        unifiTracker.MaxIdleThreashold = 0
        unifiTracker.exec_ssh_cmdline = mock0_exec_ssh_cmdline
        ap_clients = unifiTracker.get_ap_clients('user', 'testhost')
        assert((mcl.TEST_AP, mcl.TEST_CLIENTS0) == ap_clients)

    def test_diff1(self):
        '''Expected diff'''
        unifiTracker = unifi.UnifiTracker()
        unifiTracker.exec_ssh_cmdline = mock1_exec_ssh_cmdline
        last = {c['mac'].upper(): c for c in mcl.TEST_CLIENTS0}
        diff = unifiTracker.scan_aps('user', [mcl.TEST_AP], last)
        expect = ({c['mac'].upper(): c for c in mcl.TEST_CLIENTS1},
                  [mcl.TEST_CLIENTS1[1]['mac'].upper()],
                  [mcl.TEST_CLIENTS0[1]['mac'].upper()])
        assert(expect == diff)

    def test_diff2(self):
        '''Expected no diff with unordered clients.'''
        unifiTracker = unifi.UnifiTracker()
        unifiTracker.exec_ssh_cmdline = mock1_exec_ssh_cmdline
        last = {c['mac'].upper(): c for c in mcl.TEST_CLIENTS1}
        diff = unifiTracker.scan_aps('user', [mcl.TEST_AP], last)
        expect = ({c['mac'].upper(): c for c in mcl.TEST_CLIENTS2},
                  [],
                  [])
        assert(expect == diff)

if __name__ == "__main__":
    unittest.main()

