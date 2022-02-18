#!/bin/sh

# Expecting SSH default key in /root/.ssh

python3 -u /app/device_tracker.py $LOGGING_LEVEL \
                                  --loggername=$DEVICE_LOGGER_NAME \
                                  --delay=$SCAN_DELAY_SECS \
                                  --topic=$MQTT_TOPIC \
                                  --mqtthost=$MQTT_HOSTNAME \
                                  --hostlist=$UNIFI_AP_IP_LIST
