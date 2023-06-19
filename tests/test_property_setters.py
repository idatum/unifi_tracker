import os
import unittest
import unifi_tracker as unifi

class TestPropertySetters(unittest.TestCase):

    def test_ctor_parameters(self):
        useHostKeys = True
        sshTimeout = 5
        unifi_tracker = unifi.UnifiTracker(useHostKeys=useHostKeys)
        assert(useHostKeys == unifi_tracker.UseHostKeys)

    def test_useHostKeys_default(self):
        # UseHostKeys defaults to False
        useHostKeys = False
        unifi_tracker = unifi.UnifiTracker()
        assert(useHostKeys == unifi_tracker.UseHostKeys)
    
    def test_useHostKeys_setter(self):
        unifi_tracker = unifi.UnifiTracker()
        useHostKeys = not unifi_tracker.UseHostKeys
        unifi_tracker.UseHostKeys = useHostKeys
        assert(useHostKeys == unifi_tracker.UseHostKeys)

    def test_sshTimeout_default(self):
        # SshTimeout defaults to None
        sshTimeout = None
        unifi_tracker = unifi.UnifiTracker()
        assert(sshTimeout == unifi_tracker.SshTimeout)

    def test_sshTimeout_setter(self):
        unifi_tracker = unifi.UnifiTracker()
        sshTimeout = 1
        unifi_tracker.SshTimeout = sshTimeout + 1
        assert(sshTimeout + 1 == unifi_tracker.SshTimeout)

    def test_maxIdleTime_default(self):
        # MaxIdleTime defaults to None
        maxIdleTime = None
        unifi_tracker = unifi.UnifiTracker()
        assert(maxIdleTime == unifi_tracker.MaxIdleTime)

    def test_maxIdleTime_setter(self):
        unifi_tracker = unifi.UnifiTracker()
        maxIdleTime = 1
        unifi_tracker.MaxIdleTime = maxIdleTime + 1
        assert(maxIdleTime + 1 == unifi_tracker.MaxIdleTime)

    def test_processes_default(self):
        # Processes defaults to os.cpu_count()
        processes = os.cpu_count()
        unifi_tracker = unifi.UnifiTracker()
        assert(processes == unifi_tracker.Processes)

    def test_processes_setter(self):
        unifi_tracker = unifi.UnifiTracker()
        processes = 0
        unifi_tracker.Processes = processes + 1
        assert(processes + 1 == unifi_tracker.Processes)

if __name__ == "__main__":
    unittest.main()
