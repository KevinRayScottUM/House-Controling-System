#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse recognizer/output text and publish home assistant JSON commands."""
import json
import rospy
from std_msgs.msg import String
class VoiceCommandNode(object):
    def __init__(self):
        rospy.init_node('voice_command_node', anonymous=False)
        self.pub=rospy.Publisher('/home_assistant/command', String, queue_size=10)
        rospy.Subscriber('/recognizer/output', String, self.parse_asr_result, queue_size=10)
        rospy.loginfo('[voice_command_node] listening to /recognizer/output'); rospy.spin()
    def parse_asr_result(self, detected_words):
        text=detected_words.data.lower().strip(); room=self.detect_room(text); action=self.detect_action(text)
        if room and action:
            cmd={'source':'voice','room':room,'target':'master_switch','action':action}
            self.pub.publish(String(data=json.dumps(cmd))); rospy.loginfo('[voice_command_node] %s -> %s', text, cmd)
        else:
            rospy.logwarn('[voice_command_node] unrecognized: %s', text)
    def detect_room(self,text):
        if 'room one' in text or 'room 1' in text or 'bedroom' in text: return 'room_1'
        if 'room two' in text or 'room 2' in text or 'living room' in text: return 'room_2'
        if 'room three' in text or 'room 3' in text or 'toilet' in text or 'bathroom' in text: return 'room_3'
        return None
    def detect_action(self,text):
        if 'turn on' in text or 'switch on' in text or text.endswith(' on'): return 'on'
        if 'turn off' in text or 'switch off' in text or text.endswith(' off'): return 'off'
        if 'status' in text: return 'status'
        return None
if __name__=='__main__': VoiceCommandNode()
