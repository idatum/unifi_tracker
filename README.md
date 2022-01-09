MQTT Unifi AP device tracker
-
I have Ubiquiti AP devices in my home network. Previously I used Home Assistant's (HA) Unifi Direct for wifi client device tracking for presence detection.

I now use HA's MQTT device tracker to replace the unifi_direct integration. From looking at the HA github, improvements seem to be stalled on separating Unifi specific functionality. Also, I'm never really comfortable with secrets.yaml having a password with essentially full access to my router and APs -- HA has generous enough privilege on my network already.

These and other points motivated me to create a seperate Docker container service. Much of the functionality was inspired (stolen) from the existing unifi_direct integration, which generally works fine:

https://github.com/home-assistant/core/tree/dev/homeassistant/components/unifi_direct

In short: I wanted another option, one in which I have full control, seperate from HA components, other than the MQTT service which I use extensively anyway.

It is a simple service:
- 
1. Use SSH to remotely and periodically call a utility, ```mca-dump```, on Ubiquiti APs that returns JSON with client MACs; use SSH key auth.
2. Union all client MACs from all APs.
3. Do a diff between the previous and current set of MAC addresses.
4. Publish diff to MQTT (Mosquitto) for processing in HA using the MQTT service.

A couple key notes:
-
I retain MQTT messages so HA can restart and pick up current presence state. The topic has the MAC address, and the payload is "home". Here is an example HA device_tracker.yaml (included in configuraiton.yaml):
```
- platform: mqtt
  consider_home: 60
  devices:
    tracked_phone: "device_tracker/unifi_tracker/xx:xx:xx:xx:xx:xx"
  qos: 1
  source_type: router
  ```
  Note ```consider_home```: this is correctly observed by HA by deleting the retained message, and not by publishing "not_home". To delete a retained MQTT message, you publish a retained topic with no payload. Here's the code in ```device_tracker.py```:
  ```
              last_clients, added, deleted = unifi.scan_aps(ap_hosts=AP_hosts, last_mac_clients=last_clients)
            for mac in added:
                publish_state(topic=f'{Topic_base}/{mac}', state='home', retain=True)
            for mac in deleted:
                # Empty payload
                publish_state(topic=f'{Topic_base}/{mac}', state=None, retain=True)
  ```
  Notice the empty (None) state payload for a deleted device. In HA for this example, the presence for the associated Person will change to away after about a minute.

If any one AP fails to return output from ```mca-dump```, the entire diff will fail. I only have a couple APs, but if you have many, the probability of failing to do a diff increases. I get 1 or 2 failures per hour from any of the my APs (it simply doesn't return any results -- no clue why).

Works fine generally, basically like the existing unifi_direct, and is one less external dependency for running HA for my home automation.
