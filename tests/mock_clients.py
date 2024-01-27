import json

TEST_AP = "testAP"
TEST_AP2 = "testAP2"
TEST_CLIENTS0 = [{"mac": "mac1", "hostname": "hostname1", "ip": "ip1",
                  "idletime": 1, "rssi": 1, "ap_hostname": TEST_AP},
                 {"mac": "mac2", "hostname": "hostname2", "ip": "ip2",
                  "idletime": 2, "rssi": 2, "ap_hostname": TEST_AP}]
TEST_CLIENTS1 = [{"mac": "mac1", "hostname": "hostname1", "ip": "ip1",
                  "idletime": 1, "rssi": 1, "ap_hostname": TEST_AP},
                 {"mac": "mac3", "hostname": "hostname3", "ip": "ip3",
                  "idletime": 3, "rssi": 3, "ap_hostname": TEST_AP}]
TEST_CLIENTS2 = [{"mac": "mac3", "hostname": "hostname3", "ip": "ip3",
                  "idletime": 3, "rssi": 3, "ap_hostname": TEST_AP},
                 {"mac": "mac1", "hostname": "hostname1", "ip": "ip1",
                  "idletime": 1, "rssi": 1, "ap_hostname": TEST_AP}]
TEST_CLIENT4 = [{"mac": "mac4", "hostname": "hostname4", "ip": "ip4",
                  "idletime": 4, "rssi": 4, "ap_hostname": TEST_AP2}]
TEST_CLIENT4a = [{"mac": "mac4", "hostname": "hostname4", "ip": "ip4",
                  "idletime": 4, "rssi": 4, "ap_hostname": TEST_AP}]

