MQTT Unifi AP device tracker
-
I use Ubiquiti Unifi AP AC Pro devices for my home network Wifi. Previously I used Home Assistant's (HA) Unifi Direct integration for wifi client device tracking and presence detection. Generally, presence detection allows automations like turning down the heat, etc, when no one is home. My effort here is to substitute HA's Unifi Direct with an implementation that only relies on HS's MQTT device tracker functionality.

From looking at the HA github for the unifi_direct component, improvements seem to be stalled on separating Unifi specific functionality. Also, I'm never really comfortable with secrets.yaml having a password with essentially full access to my router and APs -- I prefer SSH key auth whenever possible.

These and other points motivated me to create a seperate Docker container service using MQTT to post AP client connects/disconnects. Much of the functionality to interact with the AP was inspired from the existing unifi_direct integration, which generally still works fine:

https://github.com/home-assistant/core/tree/dev/homeassistant/components/unifi_direct

In short: I wanted another option to track WiFi clients, an MQTT option in which I have full control, seperate from HA components other than the MQTT service which I use extensively anyway.

Module
-
The module ```unifi_tracker``` has the functionality to query each AP using SSH by remotely executing a Unifi utility ```mca-dump```. Only SSH key auth is supported.

Python Package Index:
https://pypi.org/project/unifi-tracker/

Example application:
- 
https://github.com/idatum/unifi_tracker/blob/main/app/device_tracker.py provides an example intended for use with HA. It's a simple service using ```unifi_tracker```:

1. Periodically return client info from all APs.
2. Union all client MACs from all APs.
3. Do a diff between the previous and current set of MAC addresses.
4. Publish diff to MQTT (Mosquitto) for processing in HA using the MQTT service.

A few key notes:
-
MQTT messages are retained so HA can restart and pick up current presence state. The topic has the MAC address, and the payload is "home". Here is an example HA device_tracker.yaml (included in configuration.yaml):
```
- platform: mqtt
  consider_home: 60
  devices:
    tracked_phone: "device_tracker/unifi_tracker/xx:xx:xx:xx:xx:xx"
  qos: 1
  source_type: router
  ```
  Note ```consider_home```: to have HA correctly honor that setting, deleting the retained message is required instead of publishing "not_home" in the payload. To delete a retained MQTT message, you publish a retained topic with no payload. Here's the code in ```device_tracker.py```:
  ```
              last_clients, added, deleted = unifiTracker.scan_aps(ap_hosts=AP_hosts, last_mac_clients=last_clients)
            for mac in added:
                publish_state(topic=f'{Topic_base}/{mac}', state='home', retain=True)
            for mac in deleted:
                # Empty payload
                publish_state(topic=f'{Topic_base}/{mac}', state=None, retain=True)
  ```
  Notice the empty (None) state payload for a deleted device. In HA for this example, the presence for the associated Person will change to away after about a minute.

If any one AP fails to return output from ```mca-dump```, the entire diff will fail. Note that clients can roam, switching from one AP to another. I only have a couple APs, but if you have many, the probability of failing to do a diff increases. I get 1 or 2 failures per hour from any of the my APs (it simply doesn't return any results -- no clue why).

I use multiprocessing.Pool to retrieve output in parallel from the APs.

There are 2 environment variables for MQTT credentials:
```
MQTT_USERNAME
MQTT_PASSWORD
```  
The Unifi AP SSH username (using SSH key auth) is also an environment variable:
```
UNIFI_SSH_USERNAME
```

In summary: ```device_tracker.py``` drives the main processing and handles MQTT, ```unifi_tracker.py``` handles SSH and client diff with APs.

Summary
-
Works fine generally, basically like the existing HA unifi_direct, and allows me to more freely innovate and be less dependent on another component for running HA for my home automation.
