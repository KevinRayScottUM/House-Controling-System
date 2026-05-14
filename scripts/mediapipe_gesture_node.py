#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MediaPipe Hands gesture node: publish left_1/left_2/left_3/right_open/right_fist."""
import json
import time
import cv2
import mediapipe as mp
import rospy
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from std_msgs.msg import String

class MediaPipeGestureNode(object):
    def __init__(self):
        rospy.init_node("mediapipe_gesture_node", anonymous=False)
        rospy.on_shutdown(self.shutdown)
        self.image_topic = rospy.get_param("~image_topic", "/usb_cam/image_raw")
        self.show_debug = bool(rospy.get_param("~show_debug", True))
        self.mirror_image = bool(rospy.get_param("~mirror_image", True))
        self.swap_hands = bool(rospy.get_param("~swap_hands", False))
        self.process_every_n = int(rospy.get_param("~process_every_n", 2))
        self.min_detection_confidence = float(rospy.get_param("~min_detection_confidence", 0.6))
        self.min_tracking_confidence = float(rospy.get_param("~min_tracking_confidence", 0.6))
        self.bridge = CvBridge()
        self.frame_count = 0
        self.last_time = time.time()
        self.pub = rospy.Publisher("/home_assistant/gesture_raw", String, queue_size=20)
        self.debug_image_pub = rospy.Publisher("/home_assistant/gesture_debug_image", Image, queue_size=1)
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        rospy.Subscriber(self.image_topic, Image, self.image_callback, queue_size=1, buff_size=10000000)
        rospy.loginfo("[mediapipe_gesture_node] subscribed to %s", self.image_topic)
        rospy.spin()

    def image_callback(self, msg):
        self.frame_count += 1
        if self.frame_count % self.process_every_n != 0:
            return
        try:
            image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as exc:
            rospy.logwarn("[mediapipe_gesture_node] CvBridge error: %s", exc)
            return
        if self.mirror_image:
            image = cv2.flip(image, 1)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        labels_to_draw = []
        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                raw_hand = handedness.classification[0].label.lower()
                score = float(handedness.classification[0].score)
                hand_side = raw_hand
                if self.swap_hands:
                    hand_side = "right" if raw_hand == "left" else "left"
                landmarks = hand_landmarks.landmark
                extended = self.count_extended_fingers(landmarks, hand_side)
                label = self.classify_gesture(hand_side, extended)
                if label:
                    event = {"label": label, "hand": hand_side, "extended_fingers": extended,
                             "confidence": score, "source": "mediapipe"}
                    self.pub.publish(String(data=json.dumps(event)))
                    labels_to_draw.append("{} fingers={} conf={:.2f}".format(label, extended, score))
                if self.show_debug:
                    self.mp_draw.draw_landmarks(image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        if self.show_debug:
            now = time.time()
            fps = 1.0 / max(now - self.last_time, 1e-6)
            self.last_time = now
            cv2.putText(image, "FPS:{:.1f}".format(fps), (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)
            for i, text in enumerate(labels_to_draw):
                cv2.putText(image, text, (20, 70 + 30*i), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,220,80), 2)
            cv2.imshow("mediapipe_gesture_node", image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                rospy.signal_shutdown("user quit")
            try:
                out = self.bridge.cv2_to_imgmsg(image, "bgr8")
                out.header.stamp = rospy.Time.now()
                self.debug_image_pub.publish(out)
            except CvBridgeError:
                pass

    def count_extended_fingers(self, lm, hand_side):
        count = 0
        for tip_id, pip_id in [(8,6), (12,10), (16,14), (20,18)]:
            if lm[tip_id].y < lm[pip_id].y:
                count += 1
        try:
            if hand_side == "right":
                thumb_extended = lm[4].x < lm[3].x
            else:
                thumb_extended = lm[4].x > lm[3].x
            if thumb_extended:
                count += 1
        except Exception:
            pass
        return count

    def classify_gesture(self, hand_side, extended):
        if hand_side == "left":
            if extended <= 0:
                return None
            if extended == 1:
                return "left_1"
            if extended == 2:
                return "left_2"
            return "left_3"
        if hand_side == "right":
            if extended >= 4:
                return "right_open"
            if extended <= 1:
                return "right_fist"
        return None

    def shutdown(self):
        cv2.destroyAllWindows()
        rospy.loginfo("[mediapipe_gesture_node] shutdown")

if __name__ == "__main__":
    MediaPipeGestureNode()
