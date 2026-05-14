#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert raw gesture labels into room master-switch commands."""
import json
import time
from collections import deque
import rospy
from std_msgs.msg import String

LEFT_ROOM_MAP = {"left_1": "room_1", "left_2": "room_2", "left_3": "room_3"}
RIGHT_ACTION_MAP = {"right_open": "on", "right_fist": "off"}

class GestureInterpreter(object):
    def __init__(self):
        rospy.init_node("gesture_interpreter", anonymous=False)
        self.confidence_threshold = float(rospy.get_param("~confidence_threshold", 0.65))
        self.stable_frames = int(rospy.get_param("~stable_frames", 3))
        self.selection_timeout_sec = float(rospy.get_param("~selection_timeout_sec", 3.0))
        self.command_cooldown_sec = float(rospy.get_param("~command_cooldown_sec", 1.2))
        self.left_history = deque(maxlen=self.stable_frames)
        self.right_history = deque(maxlen=self.stable_frames)
        self.selected_room = None
        self.selected_at = 0.0
        self.last_command_at = 0.0
        self.last_command_key = ""
        self.command_pub = rospy.Publisher("/home_assistant/command", String, queue_size=10)
        self.debug_pub = rospy.Publisher("/home_assistant/gesture_debug", String, queue_size=10)
        rospy.Subscriber("/home_assistant/gesture_raw", String, self.gesture_callback, queue_size=20)
        rospy.loginfo("[gesture_interpreter] Ready")
        rospy.spin()

    def gesture_callback(self, msg):
        try:
            event = json.loads(msg.data)
        except Exception as exc:
            rospy.logwarn("[gesture_interpreter] Bad gesture JSON: %s | %s", msg.data, exc)
            return
        label = event.get("label", "")
        confidence = float(event.get("confidence", 0.0))
        if confidence < self.confidence_threshold:
            return
        if label in LEFT_ROOM_MAP:
            self.left_history.append(label)
            stable = self.stable_label(self.left_history)
            if stable:
                self.selected_room = LEFT_ROOM_MAP[stable]
                self.selected_at = time.time()
                self.publish_debug("selected_room={}".format(self.selected_room))
        elif label in RIGHT_ACTION_MAP:
            self.right_history.append(label)
            stable = self.stable_label(self.right_history)
            if stable:
                self.try_publish_command(stable)

    def stable_label(self, history):
        if len(history) < self.stable_frames:
            return None
        first = history[0]
        if all(x == first for x in history):
            history.clear()
            return first
        return None

    def try_publish_command(self, right_label):
        now = time.time()
        if not self.selected_room:
            self.publish_debug("right gesture seen, but no room selected")
            return
        if now - self.selected_at > self.selection_timeout_sec:
            self.publish_debug("selection timeout")
            self.selected_room = None
            return
        action = RIGHT_ACTION_MAP[right_label]
        command_key = "{}:{}".format(self.selected_room, action)
        if command_key == self.last_command_key and now - self.last_command_at < self.command_cooldown_sec:
            self.publish_debug("cooldown skip {}".format(command_key))
            return
        command = {"source": "gesture", "room": self.selected_room, "target": "master_switch", "action": action}
        self.command_pub.publish(String(data=json.dumps(command)))
        self.last_command_key = command_key
        self.last_command_at = now
        self.publish_debug("published {}".format(command))

    def publish_debug(self, text):
        rospy.loginfo("[gesture_interpreter] %s", text)
        self.debug_pub.publish(String(data=text))

if __name__ == "__main__":
    GestureInterpreter()
