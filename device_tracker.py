import os
import time
import argparse
import logging
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
from multiprocessing import Queue
from multiprocessing import Process
import unifi_tracker as unifi

Log = logging.getLogger("unifi_tracker")

Retained_maxcount = 100
Retained_timeout = 1
Retained_queue = Queue(maxsize=Retained_maxcount)
Topic_base = 'device_tracker/unifi_tracker'

Mqtt_host = "mosquitto"
Mqtt_port = 1883
Mqtt_client = mqtt.Client(clean_session=True)
Mqtt_qos = 1

AP_hosts = []
Scan_delay_secs = 15
Snapshot_loop_count = int(round(60 * 60 / Scan_delay_secs, 0))


# Publish state to MQTT and retain.
def publish_state(topic: str, state: str, retain: bool=True):
    try:
        info = Mqtt_client.publish(topic=topic, payload=state, qos=Mqtt_qos, retain=retain)
        Log.debug(f"Published {topic}: {info}")
    except Exception as e:
        Log.exception(e)


# Connect to MQTT host
def mqtt_connect():
    Mqtt_client.username_pw_set(username=os.environ['MQTT_USERNAME'], password=os.environ['MQTT_PASSWORD'])
    Mqtt_client.connect(host=Mqtt_host, port=Mqtt_port)
    Mqtt_client.loop_start()


# Cleanup MQTT connection
def mqtt_disconnect():
    Mqtt_client.loop_stop()
    Mqtt_client.disconnect()


# Process callback; enqueue retained topic.
def on_retained_message(client, queue, message):
    Log.debug(message.topic)
    if not queue.full():
        queue.put_nowait(message.topic)


# Multiprocess Process method to retrieve retained topic.
# Fill queue with topics in callback.
def get_retained_messages():
    Log.debug('Started get retrained messages process')
    subscribe.callback(callback=on_retained_message, userdata=Retained_queue,
         topics=f"{Topic_base}/+",
         qos=Mqtt_qos, hostname=Mqtt_host, port=Mqtt_port, tls=None,
         auth={"username":os.environ['MQTT_USERNAME'], "password": os.environ['MQTT_PASSWORD']})


# Retrieve persisted MQTT topics for existing client MACs
def get_existing_clients():
    Log.info('Retrieving retained clients')
    try:
        p = Process(target=get_retained_messages)
        p.start()
        p.join(timeout=Retained_timeout)
        p.terminate()
        try:
            # Kill process
            p.close()
        except ValueError as e:
            Log.debug(e)
        if Retained_queue.empty():
            Log.info('No retained clients retrieved.')
            return {}
        existing_macs = {}
        while not Retained_queue.empty():
            topic = Retained_queue.get_nowait()
            if not topic:
                break
            mac = topic.split('/')[-1]
            existing_macs[mac] = {'mac': f'{mac}'}
    except Exception as e:
        Log.exception(e)
    return existing_macs


# Inner loop of processing.
# Perform diff between existing clients and last retrieved clients; publish to MQTT.
# To indicate present state, publish topic and retain with 'home' payload;
# for away state, publish topic and retain with empty payload, which per MQTT, deletes.
# If using Home Assistant MQTT device tracker, consider_home setting will be honered.
def process(last_clients):
    for i in range(Snapshot_loop_count):
        try:
            last_clients, added, deleted = unifi.scan_aps(ap_hosts=AP_hosts, last_mac_clients=last_clients)
            for mac in added:
                publish_state(f'{Topic_base}/{mac}', 'home', True)
            for mac in deleted:
                # Empty payload
                publish_state(f'{Topic_base}/{mac}', None, True)
        except unifi.UnifiTrackerException as e:
            # Too common to be a warning/error
            Log.info(e)
        time.sleep(Scan_delay_secs)


# Outer loop of processing.
# Initialize inner loop with existing persisted client MACs.
def main():
    Log.info('Starting processing loop.')
    while True:
        Log.debug("Scanning started.")
        try:
            existing_clients = get_existing_clients()
            mqtt_connect()
            process(existing_clients)
            mqtt_disconnect()
        except Exception as e:
            Log.exception(e)
        time.sleep(30)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap_log = ap.add_mutually_exclusive_group()
    ap_log.add_argument("--debug", required=False, action='store_true', default=False, help="Enable debug level logging.")
    ap_log.add_argument("--info", required=False, action='store_true', default=False, help="Enable info level logging.")
    ap_log.add_argument("--warning", required=False, action='store_true', default=False, help="Enable warning level logging.")
    ap_log.add_argument("--error", required=False, action='store_true', default=False, help="Enable error level logging.")
    ap.add_argument("--hostlist", type=str, required=True, action='store', help="List of access point IP addresses.")
    ap.add_argument("--mqtthost", type=str, required=False, action='store', default=Mqtt_host, help="MQTT host.")
    ap.add_argument("--unifiuser", type=str, required=False, action='store', default=unifi.SSH_USERNAME, help="Unifi username.")
    ap.add_argument("--topic", type=str, required=False, action='store', default=Topic_base, help="MQTT topic")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO if args.info \
                        else logging.ERROR if args.error else logging.WARNING,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        datefmt='%m-%d-%Y %H:%M:%S')
    AP_hosts = args.hostlist.split(',')
    Mqtt_host = args.mqtthost
    Topic_base = args.topic
    unifi.SSH_USERNAME = args.unifiuser
    
    Log.debug(AP_hosts)
    main()
