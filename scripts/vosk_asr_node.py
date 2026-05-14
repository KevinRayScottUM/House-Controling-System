#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
vosk_asr_node.py

Offline microphone speech recognition node for ROS1.

Microphone
    ↓
Vosk offline ASR
    ↓
/recognizer/output  std_msgs/String

This node only publishes recognized text.
The existing voice_command_node.py will parse the text and publish
/home_assistant/command.
"""

import json
import queue
import sys

import rospy
from std_msgs.msg import String

import sounddevice as sd
from vosk import Model, KaldiRecognizer


class VoskASRNode(object):
    def __init__(self):
        rospy.init_node("vosk_asr_node", anonymous=False)
        rospy.on_shutdown(self.shutdown)

        self.model_path = rospy.get_param(
            "~model_path",
            "/home/ros/catkin_ws/src/local_home_assistant/models/vosk-model-small-en-us-0.15",
        )
        self.sample_rate = int(rospy.get_param("~sample_rate", 16000))
        self.device = rospy.get_param("~device", "")
        self.show_partial = bool(rospy.get_param("~show_partial", False))

        self.grammar = [
            "turn on room one",
            "turn off room one",
            "turn on room two",
            "turn off room two",
            "turn on room three",
            "turn off room three",

            "turn on bedroom",
            "turn off bedroom",
            "turn on living room",
            "turn off living room",
            "turn on toilet",
            "turn off toilet",
            "turn on bathroom",
            "turn off bathroom",

            "bedroom status",
            "living room status",
            "toilet status",
            "bathroom status",
            "room one status",
            "room two status",
            "room three status",

            "[unk]",
        ]

        self.audio_queue = queue.Queue()
        self.pub = rospy.Publisher("/recognizer/output", String, queue_size=10)

        rospy.loginfo("[vosk_asr_node] Loading model: %s", self.model_path)
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(
            self.model,
            self.sample_rate,
            json.dumps(self.grammar),
        )

        rospy.loginfo("[vosk_asr_node] Ready.")
        rospy.loginfo("[vosk_asr_node] Try saying: turn on room one / turn off living room")

        self.run()

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            rospy.logwarn("[vosk_asr_node] Audio status: %s", status)
        self.audio_queue.put(bytes(indata))

    def run(self):
        stream_kwargs = {
            "samplerate": self.sample_rate,
            "blocksize": 8000,
            "dtype": "int16",
            "channels": 1,
            "callback": self.audio_callback,
        }

        if self.device not in ["", None]:
            stream_kwargs["device"] = self.device

        try:
            with sd.RawInputStream(**stream_kwargs):
                while not rospy.is_shutdown():
                    data = self.audio_queue.get()

                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip()

                        if text:
                            rospy.loginfo("[vosk_asr_node] FINAL: %s", text)
                            self.pub.publish(String(data=text))

                    elif self.show_partial:
                        partial = json.loads(self.recognizer.PartialResult()).get("partial", "").strip()
                        if partial:
                            rospy.loginfo("[vosk_asr_node] partial: %s", partial)

        except Exception as exc:
            rospy.logerr("[vosk_asr_node] Failed to open microphone or run ASR: %s", exc)
            rospy.logerr("[vosk_asr_node] Check Windows microphone permission and WSL audio devices.")
            sys.exit(1)

    def shutdown(self):
        rospy.loginfo("[vosk_asr_node] Shutdown.")


if __name__ == "__main__":
    VoskASRNode()
