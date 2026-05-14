#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Terminal gesture simulator: 1/2/3 select room, o=right_open, f=right_fist."""
import json
import rospy
from std_msgs.msg import String

class KeyboardGestureMock(object):
    def __init__(self):
        rospy.init_node("keyboard_gesture_mock", anonymous=False)
        self.repeat = int(rospy.get_param("~repeat", 3))
        self.pub = rospy.Publisher("/home_assistant/gesture_raw", String, queue_size=10)
        self.mapping = {
            "1": ("left_1", "left"), "2": ("left_2", "left"), "3": ("left_3", "left"),
            "o": ("right_open", "right"), "on": ("right_open", "right"),
            "f": ("right_fist", "right"), "off": ("right_fist", "right"),
        }

    def run(self):
        rospy.loginfo("[keyboard_gesture_mock] type 1/2/3/o/f/q")
        while not rospy.is_shutdown():
            s = input("gesture> ").strip().lower()
            if s in ["q", "quit", "exit"]:
                break
            if s not in self.mapping:
                print("valid: 1, 2, 3, o, f, q")
                continue
            label, hand = self.mapping[s]
            event = {"label": label, "hand": hand, "confidence": 0.99, "source": "keyboard"}
            for _ in range(self.repeat):
                self.pub.publish(String(data=json.dumps(event)))
                rospy.sleep(0.05)
            rospy.loginfo("[keyboard_gesture_mock] %s", event)

if __name__ == "__main__":
    KeyboardGestureMock().run()
