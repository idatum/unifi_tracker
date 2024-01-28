MQTT Unifi AP device tracker
-
I use Ubiquiti Unifi AP AC Pro devices for my home network Wifi. With ```unifi_tracker```, Unifi APs can be used for WiFi device tracking and presence detection.

Generally, presence detection allows [Home Assistant (HA)](https://www.home-assistant.io/) automations like changing your thermostat target temperature, etc, based on whether anyone is home. My effort here is to substitute HA's Unifi Direct with an implementation that only relies on the MQTT integration device tracker functionality. Also, I'm never really comfortable with ```secrets.yaml``` having a password with essentially full access to my router and APs -- ```unifi_tracker``` only uses SSH keys.

Much of the functionality to interact with the AP was inspired from the existing unifi_direct integration:

https://github.com/home-assistant/core/tree/dev/homeassistant/components/unifi_direct

In short: I wanted another option to track WiFi clients, an MQTT option in which I have full control, seperate from HA components other than the MQTT service which I use extensively anyway.

Module
-
The Python module ```unifi_tracker``` has the functionality to query each AP using SSH by remotely executing a Unifi utility ```mca-dump```. Only SSH key auth is supported.

Python Package Index:
https://pypi.org/project/unifi-tracker/

Example application:
- 
https://github.com/idatum/unifi_tracker/blob/main/app/device_tracker.py provides an example intended for use with HA. It's a simple service using ```unifi_tracker```:

1. Periodically return client info from all APs.
2. Either union all client MACs from all APs or group client MACs by AP hostname.
3. Do a diff between the previous and current set of MAC addresses.
4. Publish diff to MQTT (Mosquitto) for processing in HA using the MQTT service.

A few key notes:
-
MQTT messages are retained so HA can restart and pick up current presence state. The topic has the MAC address and the AP hostname if grouping by AP, and the payload is "home" or "not_home" (both configurable). Here is an example HA 2024.1.5 and above mqtt device tracker configuration:
```
mqtt:
  device_tracker:
    - name: "my_phone_north"
      state_topic: "device_tracker/unifi_tracker/northAP/xx:xx:xx:xx:xx:xx"
    - name: "my_phone_south"
      state_topic: "device_tracker/unifi_tracker/southAP/xx:xx:xx:xx:xx:xx"
  ```
Using the option to group clients by AP, this creates 2 entities for a single phone WiFi client MAC address, for the northAP and the southAP hostname APs. You can then associate both with a single user in ```SettingsPeople/Select the devices that belong to this person```.

Starting with HA 2022.9, MQTT tracked devices are no longer defined under the ```device_tracker``` platform, and are now under ```mqtt```. With this change, there is no longer a  ```consider_home``` parameter that will work with MQTT. You now need to publish a payload of "not_home". Note that presence state will now be "unknown" until an associated MQTT message is published. This may need to be accounted for in any HA automations.

Consider using the --maxIdleTime option for ```device_tracker.py``` to delay a change to "away", similar to the old behavior of ```consider_home```. Also, I recommend using the ```sshTimeout``` option to avoid potentially hanging on the SSH channel if the AP is rebooted (e.g. firmware update).

If any one AP fails to return output from ```mca-dump```, the entire diff will fail. Note that clients can roam, switching from one AP to another, and if you want to know which client is connected to which AP, use the group clients by AP option.

I only have a couple APs, but if you have many, the probability of failing to do a diff increases. I get less than 1 or 2 failures per hour from any of the my APs (sometimes it simply doesn't return any results -- no clue why).

I use multiprocessing.Pool to retrieve output in parallel from the APs (which can be turned off using the Processes setting).

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
Works fine generally, and allows me to more freely innovate and be less dependent on another component for running HA for my home automation.

History
-
### v0.1.0
- Functionality to group clients by AP hostname.
- Optimization: filter client properties to save memory.
- Improved tests.
### v0.0.9
- Bug fix: Apply ```--sshTimeout``` arg value to ```timeout``` parameter of ```paramiko.client.SSHClient exec_command()```; use local scope for Queue variable.
### v0.0.8
- Bug fix: Recreate paho.mqtt.client.Client to avoid ```ERROR:labtracker:SSL/TLS has already been configured.``` on MQTT disconnect/reconnect.
### v0.0.7
- Added device_tracker.py option ```--processes``` to control the number of concurrent processes run during AP scanning, or to run them sequentially (i.e. ```--processes=0```).
- Tested under Python11 and Debian12.
### v0.0.6
- Update README and docstrings corresponding to changes in HA 2022.9.
### v0.0.5
- Added device_tracker.py options ```--homePayload``` (default is "home") and ```--awayPayload``` for MQTT message payload, corresponding to home and away presence. Starting with HA 2022.6, if you define your devices under HA's ```mqtt``` platform instead of ```device_tracker```, you should use ```--awayPayload=not_home```.
### v0.0.4
- Missed updating module version in v0.0.3 release; now 0.0.4.
### v0.0.3
- Option ```--sshTimeout``` to explicitly set SSH connect timeout in seconds (float).

- Option ```--maxIdleTime``` to set AP client idle time threshold in seconds (int). Use ```--maxIdleTime``` to check the ```idletime``` field of ```sta_table``` and filter on clients that are below the given threshold. There are cases where I've seen a tracked client go out of range of the last connected AP yet still shows as connected for several minutes. I've been able to repro this case when a mobile phone goes out of range quickly (e.g. driving away in a car). If the mobile phone slowly goes out of range (e.g. walking away), it correctly shows as disconnected. Setting this threshold ensures the status changes in a more deterministic amount of time.
### v0.0.2
- Option ```--usehostkeys``` to use existing default host keys file (e.g. ~/.ssh/known_hosts).
### v0.0.1
- Initial release.
