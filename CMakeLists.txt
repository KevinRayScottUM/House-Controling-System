cmake_minimum_required(VERSION 3.0.2)
project(local_home_assistant)
find_package(catkin REQUIRED COMPONENTS rospy std_msgs sensor_msgs cv_bridge)
catkin_package()
catkin_install_python(PROGRAMS
  scripts/state_manager_node.py
  scripts/home_visualizer_node.py
  scripts/audio_feedback_node.py
  scripts/keyboard_gesture_mock_node.py
  scripts/gesture_interpreter_node.py
  scripts/camera_stream_node.py
  scripts/mediapipe_gesture_node.py
  scripts/voice_command_node.py
  scripts/collect_gesture_dataset.py
  scripts/vosk_asr_node.py
  scripts/vosk_asr_arecord_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
