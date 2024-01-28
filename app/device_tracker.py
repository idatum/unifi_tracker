import os
import time
import argparse
import logging
import paho.mqtt.client as mqtt
import paho.mqtt.subscribe as subscribe
from multiprocessing import Queue
from multiprocessing import Process
import unifi_tracker as unifi

Logger_name = "device_tracker"

Retained_maxcount = 100
Retained_timeout = 1
Topic_base = 'device_tracker/unifi_tracker'
Home_payload = "home"
Away_payload = None
GroupByAP = False

Mqtt_host = "mosquitto"
Mqtt_port = 1883
Mqtt_tls_set = None
Mqtt_client = None
Mqtt_qos = 1
Mqtt_username = os.environ['MQTT_USERNAME']
Mqtt_password = os.environ['MQTT_PASSWORD']

Unifi_ssh_username = os.environ['UNIFI_SSH_USERNAME']
UseHostKeysFile = False
SshTimeout = None
MaxIdleTime = None
Processes = None

Log = logging.getLogger(Logger_name)
AP_hosts = []
Scan_delay_secs = 15
# Reload retained messages and do a full snapshot of clients periodically (ideally every day).
Snapshot_loop_count = int(round(24 * 60 * (60 / Scan_delay_secs), 0))


def publish_state(topic: str, state: str, retain: bool=True):
    '''Publish state to MQTT and optionally retain.'''
    try:
        info = Mqtt_client.publish(topic=topic,
                                   payload=state,
                                   qos=Mqtt_qos,
                                   retain=retain)
        Log.debug(f"Published {topic}: {info}")
    except Exception as e:
        Log.exception(e)


def mqtt_connect():
    '''Connect to MQTT host.'''
    global Mqtt_client

    Mqtt_client = mqtt.Client(clean_session=True)
    if Mqtt_username is not None:
        Mqtt_client.username_pw_set(username=os.environ['MQTT_USERNAME'],
                                    password=os.environ['MQTT_PASSWORD'])
    if Mqtt_tls_set is not None:
        Log.debug('Using TLS')
        Mqtt_client.tls_set()
    Mqtt_client.connect(host=Mqtt_host, port=Mqtt_port)
    Mqtt_client.loop_start()


def mqtt_disconnect():
    '''Cleanup MQTT connection.'''
    Mqtt_client.loop_stop()
    Mqtt_client.disconnect()


def on_retained_message(_, queue, message):
    '''Process callback; enqueue retained topic.'''
    Log.debug(message.topic)
    if not queue.full():
        queue.put_nowait(message.topic)


def get_retained_messages(retained_queue):
    '''Multiprocess Process method to retrieve retained topic.
    Fill queue with topics in callback.
    '''
    Log.debug('Started get retrained messages process')
    try:
        subscribe.callback(callback=on_retained_message,
                           userdata=retained_queue,
                           topics=f"{Topic_base}/+/+" if GroupByAP else f"{Topic_base}/+",
                           qos=Mqtt_qos,
                           hostname=Mqtt_host,
                           port=Mqtt_port,
                           tls=Mqtt_tls_set,
                           auth={"username":Mqtt_username,
                                 "password": Mqtt_password})
    except Exception as e:
        Log.exception(e)


def get_existing_clients():
    '''Retrieve persisted MQTT topics for existing client MACs'''
    retained_queue = Queue(maxsize=Retained_maxcount)
    Log.info('Retrieving retained clients')
    try:
        p = Process(target=get_retained_messages, args=(retained_queue,))
        p.start()
        p.join(timeout=Retained_timeout)
        p.terminate()
        try:
            # Kill process
            p.close()
        except ValueError as e:
            Log.debug(e)
        if retained_queue.empty():
            Log.info('No retained clients retrieved.')
            return {}
        existing_macs = {}
        while not retained_queue.empty():
            topic = retained_queue.get_nowait()
            if not topic:
                break
            Log.debug(f"Existing {topic}")
            mac = topic.split('/')[-1]
            if GroupByAP:
                ap_hostname = topic.split('/')[-2]
                existing_macs[mac] = {'mac': f'{mac}', 'ap_hostname': f'{ap_hostname}'}
            else:
                existing_macs[mac] = {'mac': f'{mac}'}
    except Exception as e:
        Log.exception(e)
    return existing_macs


def process_all(unifiTracker, last_clients):
    last_clients, added, deleted = unifiTracker.scan_aps(ssh_username=Unifi_ssh_username,
                                                            ap_hosts=AP_hosts,
                                                            last_mac_clients=last_clients)
    for mac in added:
        publish_state(topic=f'{Topic_base}/{mac}', state=Home_payload, retain=True)
    for mac in deleted:
        publish_state(topic=f'{Topic_base}/{mac}', state=Away_payload, retain=True)
    return last_clients


def process_by_ap(unifiTracker, last_clients):
    last_clients, added_by_ap, deleted_by_ap = unifiTracker.scan_by_ap(ssh_username=Unifi_ssh_username,
                                                                        ap_hosts=AP_hosts,
                                                                        last_mac_clients=last_clients)
    for ap_hostname in added_by_ap:
        for mac in added_by_ap[ap_hostname]:
            publish_state(topic=f'{Topic_base}/{ap_hostname}/{mac}', state=Home_payload, retain=True)
    for ap_hostname in deleted_by_ap:
        for mac in deleted_by_ap[ap_hostname]:
            publish_state(topic=f'{Topic_base}/{ap_hostname}/{mac}', state=Away_payload, retain=True)
    return last_clients


def process(last_clients):
    '''Inner loop of processing.
    Perform diff between existing clients and last retrieved clients; publish to MQTT.
    To indicate present state, publish topic and retain with 'home' payload;
    for away state, publish topic and retain with 'not_home' payload'.
    '''
    unifiTracker = unifi.UnifiTracker(useHostKeys=UseHostKeysFile)
    if SshTimeout is not None:
        unifiTracker.SshTimeout = SshTimeout
    if MaxIdleTime is not None:
        unifiTracker.MaxIdleTime = MaxIdleTime
    if Processes is not None:
        unifiTracker.Processes = Processes
    for i in range(Snapshot_loop_count):
        try:
            if GroupByAP:
                last_clients = process_by_ap(unifiTracker, last_clients)
            else:
                last_clients = process_all(unifiTracker, last_clients)
        except unifi.UnifiTrackerException as e:
            # Too common to be a warning/error
            Log.info(e)
        time.sleep(Scan_delay_secs)


def main():
    '''Outer loop of processing.
    Initialize inner loop with existing persisted client MACs.
    '''
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
    ap.add_argument("--loggername", type=str, required=False, action='store', default=Logger_name, help="Logger name.")
    ap.add_argument("--hostlist", type=str, required=True, action='store', help="List of access point IP addresses.")
    ap.add_argument("--usehostkeys", required=False, action='store_true', default=UseHostKeysFile, help="Use known_hosts file.")
    ap.add_argument("--sshTimeout", type=float, required=False, action='store', default=SshTimeout, help="SSH timeout in secs.")
    ap.add_argument("--maxIdleTime", type=int, required=False, action='store', default=MaxIdleTime, help="Maximum AP client idle time in secs.")
    ap.add_argument("--processes", type=int, required=False, action='store', default=Processes, help="Scans run in parallel; set to 0 for sequential.")
    ap.add_argument("--mqtthost", type=str, required=False, action='store', default=Mqtt_host, help="MQTT host.")
    ap.add_argument("--mqttport", type=int, required=False, action='store', default=Mqtt_port, help="MQTT port.")
    ap.add_argument("--mqtts", required=False, action='store_true', default=False, help="Use MQTT TLS.")
    ap.add_argument("--topic", type=str, required=False, action='store', default=Topic_base, help="MQTT topic.")
    ap.add_argument("--homePayload", type=str, required=False, action='store', default=Home_payload, help="Home payload.")
    ap.add_argument("--awayPayload", type=str, required=False, action='store', default=Away_payload, help="Away payload.")
    ap.add_argument("--delay", type=int, required=False, action='store', default=Scan_delay_secs, \
                               choices=range(1,61), metavar="{1..61}", help="Loop delay seconds.")
    ap.add_argument("--groupByAP", required=False, action='store_true', default=GroupByAP, help="Group clients by AP hostname.")

    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO if args.info \
                        else logging.ERROR if args.error else logging.WARNING,
                        format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
                        datefmt='%m-%d-%Y %H:%M:%S')
    if args.loggername != Logger_name:
        Logger_name = args.loggername
        Log = logging.getLogger(Logger_name)
        unifi._LOGGER = Log
    AP_hosts = args.hostlist.split(',')
    UseHostKeysFile = args.usehostkeys
    SshTimeout = args.sshTimeout
    MaxIdleTime = args.maxIdleTime
    Processes = args.processes
    Log.debug(AP_hosts)
    Mqtt_host = args.mqtthost
    Mqtt_port = args.mqttport
    Mqtt_tls_set = {} if args.mqtts else None
    Topic_base = args.topic
    Home_payload = args.homePayload
    Away_payload = args.awayPayload
    Scan_delay_secs = args.delay
    GroupByAP = args.groupByAP

    main()
