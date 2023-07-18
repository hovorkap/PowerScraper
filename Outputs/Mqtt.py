import logging
import os
import yaml
from paho.mqtt import client as mqtt
import sys
import json

DISCOVERY_PREFIX = "homeassistant"

logger = logging.getLogger(__name__)
if "DEBUG" in os.environ:
    logger.setLevel(logging.DEBUG)

class Device(dict):
    def __init__(self, identifiers, name, sw_version, model, manufacturer):
        super().__init__()

        self.name = name

        self["identifiers"] = identifiers
        self["name"] = name
        self["sw_version"] = sw_version
        self["model"] = model
        self["manufacturer"] = manufacturer

    @staticmethod
    def from_config(config_yaml_path):
        with open(config_yaml_path) as file:
            device_config = json.loads(file.read())['device']
            device = Device(**device_config)
            return device


class Component:
    def __init__(self, name):
        self.component = name
        self.value_read_function = None

    def set_value_read_function(self, function):
        self.value_read_function = function


class Sensor(Component):
    def __init__(
            self,
            client: mqtt.Client,
            name,
            parent_device,
            device_class="None",
            unit_of_measurement="",
            icon=None,
            topic_parent_level="",
            force_update=False,
            
    ):
        super().__init__("sensor")

        self.client = client
        self.name = name
        self.parent_device = parent_device
        self.force_update = force_update
        self.object_id = self.name.replace(" ", "_").lower()
        self.unit_of_measurement = unit_of_measurement
        self.icon = icon
        self.topic_parent_level = topic_parent_level
        self.topic = f"{self.parent_device.name}/{self.component}/{self.object_id}"
        self.device_class = device_class
        self._send_config()

    def _send_config(self):
        _config = {
            "~": self.topic,
            "name": self.name,
            "state_topic": "~/state",
            "unit_of_measurement": self.unit_of_measurement,
            "device": self.parent_device,
            "force_update": self.force_update,
            "device_class": self.device_class,
            "unique_id": f"{self.parent_device.name}_{self.parent_device['identifiers']}_{self.name}".replace(" ", "_").lower()
        }

        if self.icon:
            _config["icon"] = self.icon

        self.client.publish(
            f"{DISCOVERY_PREFIX}/{self.component}/{self.parent_device.name}/{self.object_id}/config",
            json.dumps(_config),
            retain=True,
        ).wait_for_publish()

    def send(self, value=None, blocking=False):
        if value is None:
            if not self.value_read_function:
                raise ValueError("Set either value or value_read_function")

            publish_value = self.value_read_function()
        else:
            publish_value = value

        logger.debug(f"{self.topic}: {publish_value}")

        message_info = self.client.publish(f"{self.topic}/state", publish_value)

        if blocking:
            message_info.wait_for_publish()


class Tracker:
    def __init__(self, client: mqtt.Client, name):
        self.client = client
        self.name = name
        self.unique_id = self.name.replace(" ", "_").lower()
        self.topic = f"{DISCOVERY_PREFIX}/device_tracker/{self.unique_id}"
        self._send_config()

    def _send_config(self):
        _config = {
            "~": self.topic,
            "name": self.name,
            "unique_id": self.unique_id,
            "stat_t": "~/state",
            "json_attr_t": "~/attributes",
            "payload_home": "home",
            "payload_not_home": "not_home",
        }
        self.client.publish(f"{self.topic}/config", json.dumps(_config))

    def send(self, latitude, longitude, gps_accuracy):
        _payload = {
            "latitude": latitude,
            "longitude": longitude,
            "gps_accuracy": gps_accuracy,
        }
        self.client.publish(f"{self.topic}/attributes", json.dumps(_payload))


class Binary:
    def __init__(self, client: mqtt.Client, name, icon):
        self.client = client
        self.name = name
        self.unique_id = self.name.replace(" ", "_").lower()
        self.topic = f"{DISCOVERY_PREFIX}/binary_sensor/{self.unique_id}"
        self.icon = icon
        self._send_config()

    def _send_config(self):
        _config = {
            "~": self.topic,
            "name": self.name,
            "unique_id": self.unique_id,
            "stat_t": "~/state",
            "icon": self.icon,
        }
        self.client.publish(f"{self.topic}/config", json.dumps(_config))

    def send(self, value):
        self.client.publish(f"{self.topic}/state", str(value))

class Mqtt(object):
    def __init__(self, config):
        self.mqtt_host = config['mqtt_host']
        self.mqtt_port = config['mqtt_port']
        self.mqtt_keepalive = config['mqtt_keepalive']
        self.mqtt_user = config['mqtt_user']
        self.mqtt_pass = config['mqtt_pass']
        self.mqtt_topic = config['mqtt_topic']

    def on_connect(client, userdata, flags, rc):
        if rc != 0:
            print("Failed to connect, return code %d\n", rc)



    def send(self, vals, batteryAPI):
        client = mqtt.Client()
        client.username_pw_set(username=self.mqtt_user, password=self.mqtt_pass)
        client.connect(self.mqtt_host, self.mqtt_port, self.mqtt_keepalive)

        inverterDetails = vals.copy()
        inverterDetails.pop('#SolaxClient', None)
        
        dict = {key: value for key, value in inverterDetails.items()}
        values = json.dumps(dict)
        name = dict['name']
            
        inverterDevice = Device.from_config("/data/options.json")
        for x, y in inverterDetails.items():
            Sensor(
               client,
               x,
               parent_device=inverterDevice,
               unit_of_measurement=y.get('unit_of_measurement'),
               device_class=y.get('device_class')

            ).send(y.get('payload'))




        client.disconnect()
