#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenCV camera/phone-stream publisher for ROS1."""
import cv2
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


def parse_source(source):
    text = str(source).strip()
    return int(text) if text.isdigit() else text

class CameraStreamNode(object):
    def __init__(self):
        rospy.init_node("camera_stream_node", anonymous=False)
        rospy.on_shutdown(self.shutdown)
        self.camera_source = parse_source(rospy.get_param("~camera_source", "0"))
        self.image_topic = rospy.get_param("~image_topic", "/usb_cam/image_raw")
        self.fps = float(rospy.get_param("~fps", 15.0))
        self.width = int(rospy.get_param("~width", 640))
        self.height = int(rospy.get_param("~height", 480))
        self.show_debug = bool(rospy.get_param("~show_debug", False))
        self.bridge = CvBridge()
        self.pub = rospy.Publisher(self.image_topic, Image, queue_size=1)
        self.cap = cv2.VideoCapture(self.camera_source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        if not self.cap.isOpened():
            rospy.logerr("[camera_stream_node] cannot open source: %s", self.camera_source)
            return
        rospy.loginfo("[camera_stream_node] publishing %s from %s", self.image_topic, self.camera_source)
        self.loop()

    def loop(self):
        rate = rospy.Rate(self.fps)
        while not rospy.is_shutdown():
            ok, frame = self.cap.read()
            if not ok:
                rospy.logwarn_throttle(2.0, "[camera_stream_node] failed to read frame")
                rate.sleep()
                continue
            msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            msg.header.stamp = rospy.Time.now()
            msg.header.frame_id = "camera"
            self.pub.publish(msg)
            if self.show_debug:
                cv2.imshow("camera_stream_node", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    rospy.signal_shutdown("user quit")
            rate.sleep()

    def shutdown(self):
        if hasattr(self, "cap") and self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        rospy.loginfo("[camera_stream_node] shutdown")

if __name__ == "__main__":
    CameraStreamNode()
