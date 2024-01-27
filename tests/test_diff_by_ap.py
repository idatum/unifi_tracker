import unittest
import json
import unifi_tracker as unifi
import mock_clients as mcl


def mock0_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    if host == mcl.TEST_AP:
        return (json.dumps({"hostname": mcl.TEST_AP,
                                "vap_table": [{"sta_table": mcl.TEST_CLIENTS0}]}).encode(), b'')
    else:
        return (json.dumps({"hostname": mcl.TEST_AP2,
                                "vap_table": [{"sta_table": mcl.TEST_CLIENT4}]}).encode(), b'')

def mock1_exec_ssh_cmdline(user: str=None, host: str=None, cmdline: str=None):
    if host == mcl.TEST_AP:
        return (json.dumps({"hostname": mcl.TEST_AP,
                                "vap_table": [{"sta_table": mcl.TEST_CLIENTS0}]}).encode(), b'')
    else:
        return (json.dumps({"hostname": mcl.TEST_AP,
                                "vap_table": [{"sta_table": mcl.TEST_CLIENT4a}]}).encode(), b'')

class TestDiff(unittest.TestCase):

    def setUp(self):
        pass

    def test_simple(self):
        ''' Scan 2 APs with no added.'''
        unifiTracker = unifi.UnifiTracker()
        unifiTracker.exec_ssh_cmdline = mock0_exec_ssh_cmdline
        unifiTracker.Processes = 0
        scan = unifiTracker.scan_aps('user', [mcl.TEST_AP, mcl.TEST_AP2])
        added = [c['mac'].upper() for c in mcl.TEST_CLIENTS0 + mcl.TEST_CLIENT4]
        expect = ({c['mac'].upper(): c for c in mcl.TEST_CLIENTS0 + mcl.TEST_CLIENT4},
                  added,
                  [])
        assert(scan == expect)

    def test_diff_by_ap1(self):
        ''' Collect clients from 2 APs. '''
        unifiTracker = unifi.UnifiTracker()
        unifiTracker.Processes = 2
        unifiTracker.exec_ssh_cmdline = mock0_exec_ssh_cmdline
        scan = unifiTracker.scan_by_ap('user', [mcl.TEST_AP, mcl.TEST_AP2])
        added = {mcl.TEST_AP: [c['mac'].upper() for c in mcl.TEST_CLIENTS0],
                 mcl.TEST_AP2: [c['mac'].upper() for c in mcl.TEST_CLIENT4]}
        expect = ({c['mac'].upper(): c for c in mcl.TEST_CLIENTS0 + mcl.TEST_CLIENT4},
                  added,
                  {})
        assert(scan == expect)
    
    def test_diff_by_ap2(self):
        ''' Diff 2 separate AP scans.'''
        unifiTracker = unifi.UnifiTracker()
        unifiTracker.Processes = 0
        last = {c['mac'].upper(): c for c in mcl.TEST_CLIENTS0 + mcl.TEST_CLIENT4}
        unifiTracker.exec_ssh_cmdline = mock1_exec_ssh_cmdline
        scan = unifiTracker.scan_by_ap('user', [mcl.TEST_AP, mcl.TEST_AP2], last)
        added = {mcl.TEST_AP: [c['mac'].upper() for c in mcl.TEST_CLIENT4a]}
        deleted = {mcl.TEST_AP2: [c['mac'].upper() for c in mcl.TEST_CLIENT4]}
        expect = ({c['mac'].upper(): c for c in mcl.TEST_CLIENTS0 + mcl.TEST_CLIENT4a},
                  added,
                  deleted)
        assert(scan == expect)

if __name__ == "__main__":
    unittest.main()

