#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
vosk_asr_arecord_node.py

Stable WSL-friendly offline ASR node.

This node avoids sounddevice / PortAudio.
It uses arecord to capture microphone audio from PulseAudio,
then feeds raw PCM audio to Vosk.

Audio path:
    Windows Microphone
        -> WSLg PulseAudio RDPSource
        -> arecord -D pulse
        -> Vosk
        -> /recognizer/output
"""

import json
import os
import signal
import subprocess
import sys

import rospy
from std_msgs.msg import String
from vosk import Model, KaldiRecognizer


class VoskASRArecordNode(object):
    def __init__(self):
        rospy.init_node("vosk_asr_arecord_node", anonymous=False)
        rospy.on_shutdown(self.shutdown)

        self.model_path = rospy.get_param(
            "~model_path",
            "/home/ros/catkin_ws/src/local_home_assistant/models/vosk-model-small-en-us-0.15",
        )

        # Your WSL RDPSource is 44100Hz, so 44100 is the safest first choice.
        self.sample_rate = int(rospy.get_param("~sample_rate", 44100))
        self.audio_device = rospy.get_param("~audio_device", "pulse")
        self.chunk_size = int(rospy.get_param("~chunk_size", 4096))
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

        self.pub = rospy.Publisher("/recognizer/output", String, queue_size=10)

        rospy.loginfo("[vosk_asr_arecord_node] Loading model: %s", self.model_path)
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(
            self.model,
            self.sample_rate,
            json.dumps(self.grammar),
        )

        self.process = None

        rospy.loginfo("[vosk_asr_arecord_node] Ready.")
        rospy.loginfo("[vosk_asr_arecord_node] Try saying: turn on room one / turn off living room")

        self.run()

    def run(self):
        cmd = [
            "arecord",
            "-D", self.audio_device,
            "-f", "S16_LE",
            "-r", str(self.sample_rate),
            "-c", "1",
            "-t", "raw",
            "-q",
        ]

        rospy.loginfo("[vosk_asr_arecord_node] Starting audio command: %s", " ".join(cmd))

        env = os.environ.copy()
        env["PULSE_SERVER"] = env.get("PULSE_SERVER", "unix:/mnt/wslg/PulseServer")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid,
            )
        except Exception as exc:
            rospy.logerr("[vosk_asr_arecord_node] Failed to start arecord: %s", exc)
            sys.exit(1)

        if self.process.stdout is None:
            rospy.logerr("[vosk_asr_arecord_node] arecord stdout is None")
            sys.exit(1)

        while not rospy.is_shutdown():
            data = self.process.stdout.read(self.chunk_size)

            if not data:
                rospy.logerr("[vosk_asr_arecord_node] No audio data from arecord.")
                self.print_arecord_error()
                break

            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()

                if text:
                    rospy.loginfo("[vosk_asr_arecord_node] FINAL: %s", text)
                    self.pub.publish(String(data=text))

            elif self.show_partial:
                partial = json.loads(self.recognizer.PartialResult()).get("partial", "").strip()
                if partial:
                    rospy.loginfo("[vosk_asr_arecord_node] partial: %s", partial)

    def print_arecord_error(self):
        if self.process and self.process.stderr:
            try:
                err = self.process.stderr.read().decode("utf-8", errors="ignore")
                if err.strip():
                    rospy.logerr("[vosk_asr_arecord_node] arecord error:\n%s", err)
            except Exception:
                pass

    def shutdown(self):
        rospy.loginfo("[vosk_asr_arecord_node] Shutdown.")

        if self.process is not None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception:
                try:
                    self.process.terminate()
                except Exception:
                    pass


if __name__ == "__main__":
    VoskASRArecordNode()
