#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Central state manager for the ROS1 local home assistant."""
import copy
import json
import os
import rospy
from std_msgs.msg import String

try:
    import yaml
except ImportError:
    yaml = None

DEFAULT_ROOMS = {
    "room_1": {"label": "Room 1 | Bedroom", "master": False,
               "devices": {"light": False, "fan": False, "ac": False, "door": False}},
    "room_2": {"label": "Room 2 | Living Room", "master": False,
               "devices": {"light": False, "fan": False, "curtain": False, "door": False}},
    "room_3": {"label": "Room 3 | Toilet", "master": False,
               "devices": {"light": False, "exhaust": False, "heater": False, "door": False}},
}

class HomeStateManager(object):
    def __init__(self):
        rospy.init_node("home_state_manager", anonymous=False)
        rospy.on_shutdown(self.shutdown)
        self.rooms = self.load_rooms()
        self.selected_room = "room_1"
        self.last_action = "System started. Waiting for command."
        self.last_source = "system"
        self.state_pub = rospy.Publisher("/home_assistant/state", String, queue_size=10, latch=True)
        rospy.Subscriber("/home_assistant/command", String, self.command_callback, queue_size=10)
        rospy.loginfo("[home_state_manager] Ready")
        self.publish_state()
        rospy.spin()

    def load_rooms(self):
        rooms_yaml = rospy.get_param("~rooms_yaml", "")
        if rooms_yaml and os.path.exists(rooms_yaml) and yaml is not None:
            with open(rooms_yaml, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            rooms = {}
            for room_key, room_data in data.get("rooms", {}).items():
                rooms[room_key] = {
                    "label": room_data.get("label", room_key),
                    "master": False,
                    "devices": room_data.get("devices", {}),
                }
            return rooms
        return copy.deepcopy(DEFAULT_ROOMS)

    def command_callback(self, msg):
        try:
            command = json.loads(msg.data)
        except Exception as exc:
            rospy.logwarn("[home_state_manager] Bad command JSON: %s | %s", msg.data, exc)
            return

        source = command.get("source", "unknown")
        room = command.get("room")
        target = command.get("target", "master_switch")
        action = command.get("action")

        if room not in self.rooms:
            self.last_source = source
            self.last_action = "Invalid room: {}".format(room)
            self.publish_state()
            return

        self.selected_room = room

        if target == "master_switch":
            if action in ["on", "open", "true", True]:
                self.set_room_master(room, True, source)
            elif action in ["off", "close", "false", False]:
                self.set_room_master(room, False, source)
            elif action == "toggle":
                self.set_room_master(room, not self.rooms[room]["master"], source)
            elif action == "status":
                self.last_source = source
                self.last_action = self.status_text(room)
            else:
                self.last_source = source
                self.last_action = "Unknown master action: {}".format(action)
        else:
            self.set_device_state(room, target, action, source)

        self.publish_state()

    def set_room_master(self, room, on, source):
        self.rooms[room]["master"] = bool(on)
        for device_key in self.rooms[room]["devices"]:
            self.rooms[room]["devices"][device_key] = bool(on)
        self.last_source = source
        self.last_action = "{} master switch {}".format(
            self.rooms[room]["label"].split("|")[0].strip(), "ON" if on else "OFF")
        rospy.loginfo("[home_state_manager] %s", self.last_action)

    def set_device_state(self, room, target, action, source):
        if target not in self.rooms[room]["devices"]:
            self.last_source = source
            self.last_action = "Invalid device {} in {}".format(target, room)
            return
        if action in ["on", "open", "true", True]:
            value = True
        elif action in ["off", "close", "false", False]:
            value = False
        elif action == "toggle":
            value = not self.rooms[room]["devices"][target]
        else:
            self.last_source = source
            self.last_action = "Unknown device action: {}".format(action)
            return
        self.rooms[room]["devices"][target] = value
        self.rooms[room]["master"] = any(self.rooms[room]["devices"].values())
        self.last_source = source
        self.last_action = "{} {} {}".format(
            self.rooms[room]["label"].split("|")[0].strip(), target, "ON/OPEN" if value else "OFF/CLOSED")

    def status_text(self, room):
        items = []
        for k, v in self.rooms[room]["devices"].items():
            items.append("{} {}".format(k, "on/open" if v else "off/closed"))
        return "{}: {}".format(self.rooms[room]["label"].split("|")[0].strip(), ", ".join(items))

    def publish_state(self):
        payload = {
            "stamp": rospy.Time.now().to_sec(),
            "rooms": self.rooms,
            "selected_room": self.selected_room,
            "last_action": self.last_action,
            "last_source": self.last_source,
        }
        self.state_pub.publish(String(data=json.dumps(payload)))

    def shutdown(self):
        rospy.loginfo("[home_state_manager] Shutdown")

if __name__ == "__main__":
    HomeStateManager()
