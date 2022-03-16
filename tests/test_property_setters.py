import unittest
import unifi_tracker as unifi

class TestPropertySetters(unittest.TestCase):

    def test_ctor_default(self):
        # UseHostKeys defaults to False
        useHostKeys = False
        unifi_tracker = unifi.UnifiTracker()
        assert(useHostKeys == unifi_tracker.UseHostKeys)
    
    def test_ctor_value(self):
        useHostKeys = True
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

if __name__ == "__main__":
    unittest.main()
