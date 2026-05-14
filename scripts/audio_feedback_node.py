#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Log or espeak feedback for state changes."""
import json, shutil, subprocess
import rospy
from std_msgs.msg import String
class AudioFeedbackNode(object):
    def __init__(self):
        rospy.init_node('audio_feedback_node', anonymous=False)
        self.enable_tts=bool(rospy.get_param('~enable_tts', False)); self.last_action=''
        if self.enable_tts and not shutil.which('espeak'):
            rospy.logwarn('[audio_feedback_node] espeak not found; log only'); self.enable_tts=False
        rospy.Subscriber('/home_assistant/state', String, self.state_callback, queue_size=10)
        rospy.loginfo('[audio_feedback_node] ready enable_tts=%s', self.enable_tts); rospy.spin()
    def state_callback(self,msg):
        try: state=json.loads(msg.data)
        except Exception: return
        action=state.get('last_action','')
        if not action or action==self.last_action: return
        self.last_action=action; rospy.loginfo('[audio_feedback_node] %s', action)
        if self.enable_tts:
            subprocess.Popen(['espeak', action])
if __name__=='__main__': AudioFeedbackNode()
