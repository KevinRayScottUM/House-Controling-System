# House-Controling-System

A lightweight ROS1-based local multi-modal home assistant prototype.

This project demonstrates a local offline home-control system using:

- Camera-based hand gesture recognition
- Offline voice command recognition
- ROS topic-based state management
- A Pygame 2D room simulator
- Local visual and audio feedback

The system currently controls three simulated rooms:

| Room | Devices |
|---|---|
| Room 1 / Bedroom | Light, Fan, Air Conditioner, Door |
| Room 2 / Living Room | Light, Fan, Curtain, Door |
| Room 3 / Toilet | Light, Exhaust Fan, Water Heater, Door |

The current prototype focuses on a room-level master switch:

- Left hand gesture `1 / 2 / 3` selects Room 1 / Room 2 / Room 3
- Right open palm means ON
- Right fist means OFF
- Voice commands can also control the same rooms

---

## 1. System Pipeline

### Gesture Control Pipeline

```text
Android IP Camera
    ↓
camera_stream_node.py
    ↓
/usb_cam/image_raw
    ↓
mediapipe_gesture_node.py
    ↓
/home_assistant/gesture_raw
    ↓
gesture_interpreter_node.py
    ↓
/home_assistant/command
    ↓
state_manager_node.py
    ↓
/home_assistant/state
    ↓
home_visualizer_node.py
```

### Voice Control Pipeline

```text
Microphone
    ↓
arecord + Vosk Offline ASR
    ↓
vosk_asr_arecord_node.py
    ↓
/recognizer/output
    ↓
voice_command_node.py
    ↓
/home_assistant/command
    ↓
state_manager_node.py
    ↓
/home_assistant/state
    ↓
home_visualizer_node.py
```

Both gesture control and voice control publish commands into the same ROS state manager, so both modalities control the same simulated home state.

---

## 2. Project Structure

```text
local_home_assistant/
├── config/
│   ├── gesture_rules.yaml
│   └── rooms.yaml
├── dataset/
├── docs/
│   └── YOLOV5_TRAINING_NOTES.md
├── launch/
│   ├── home_assistant_base.launch
│   ├── home_assistant_camera_mediapipe.launch
│   ├── home_assistant_keyboard_demo.launch
│   └── home_assistant_voice_demo.launch
├── models/
├── scripts/
│   ├── audio_feedback_node.py
│   ├── camera_stream_node.py
│   ├── collect_gesture_dataset.py
│   ├── gesture_interpreter_node.py
│   ├── home_visualizer_node.py
│   ├── keyboard_gesture_mock_node.py
│   ├── mediapipe_gesture_node.py
│   ├── state_manager_node.py
│   ├── voice_command_node.py
│   ├── vosk_asr_arecord_node.py
│   └── vosk_asr_node.py
├── CMakeLists.txt
├── package.xml
└── README.md
```

---

## 3. Environment Setup

This project was tested in WSL with ROS Noetic.

Activate ROS and the project Python environment:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate
```

Install common dependencies:

```bash
sudo apt update
sudo apt install -y \
  ros-noetic-cv-bridge \
  ros-noetic-image-transport \
  python3-opencv \
  python3-pip \
  python3-venv \
  pulseaudio-utils \
  alsa-utils \
  libasound2-plugins \
  portaudio19-dev \
  espeak \
  unzip \
  wget
```

Install Python packages:

```bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

python -m pip install pygame pyyaml mediapipe vosk sounddevice requests
```

Build the ROS package:

```bash
cd ~/catkin_ws
source /opt/ros/noetic/setup.bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

catkin_make --pkg local_home_assistant
source ~/catkin_ws/devel/setup.bash
```

---

## 4. Download Vosk Offline ASR Model

The Vosk model is not included in this repository because it is large.

Download the small English model:

```bash
mkdir -p ~/catkin_ws/src/local_home_assistant/models
cd ~/catkin_ws/src/local_home_assistant/models

wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

After extraction, the model path should be:

```text
~/catkin_ws/src/local_home_assistant/models/vosk-model-small-en-us-0.15
```

---

## 5. Final Full System Startup

The complete system uses three terminals.

Before starting:

1. Start the Android IP Camera / IP Webcam app.
2. Confirm the camera URL.
3. Confirm that the microphone is available in WSL.
4. Replace the example camera URL with your actual device URL if needed.

Current tested camera URL example:

```text
http://192.168.0.205:8080/video
```

---

### Terminal 1: Start GUI + Camera + MediaPipe Gesture Recognition

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

roslaunch local_home_assistant home_assistant_camera_mediapipe.launch \
camera_source:="http://192.168.0.205:8080/video"
```

This starts:

```text
home_state_manager
audio_feedback_node
home_visualizer_node
camera_stream_node
mediapipe_gesture_node
gesture_interpreter_node
```

Expected windows:

```text
1. Pygame 2D Room Simulator
2. MediaPipe gesture debug window
```

Gesture controls:

```text
Left hand 1 + right open palm  -> Room 1 ON
Left hand 1 + right fist       -> Room 1 OFF
Left hand 2 + right open palm  -> Room 2 ON
Left hand 2 + right fist       -> Room 2 OFF
Left hand 3 + right open palm  -> Room 3 ON
Left hand 3 + right fist       -> Room 3 OFF
```

If left and right hands are reversed:

```bash
roslaunch local_home_assistant home_assistant_camera_mediapipe.launch \
camera_source:="http://192.168.0.205:8080/video" \
swap_hands:=true
```

If the camera image is mirrored incorrectly:

```bash
roslaunch local_home_assistant home_assistant_camera_mediapipe.launch \
camera_source:="http://192.168.0.205:8080/video" \
mirror_image:=false
```

---

### Terminal 2: Start Voice Command Parser

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

rosrun local_home_assistant voice_command_node.py
```

This node listens to:

```text
/recognizer/output
```

and converts recognized text into:

```text
/home_assistant/command
```

Supported example commands:

```text
turn on room one
turn off room one
turn on room two
turn off room two
turn on room three
turn off room three
turn on bedroom
turn off bedroom
turn on living room
turn off living room
turn on toilet
turn off toilet
```

---

### Terminal 3: Start Offline Vosk Microphone Recognition

For WSLg microphone input:

```bash
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

export PULSE_SERVER=unix:/mnt/wslg/PulseServer
pactl set-default-source RDPSource

rosrun local_home_assistant vosk_asr_arecord_node.py \
_sample_rate:=44100 \
_audio_device:=pulse \
_chunk_size:=4096
```

If successful, this terminal should show:

```text
[vosk_asr_arecord_node] FINAL: turn on room one
```

The recognized text is published to:

```text
/recognizer/output
```

Then `voice_command_node.py` converts it into a home-control command.

---

## 6. Camera Device Testing

### 6.1 Test Android IP Webcam URL

Use this if the camera comes from a phone app such as IP Webcam.

Replace the URL with your actual phone camera stream:

```bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

python - <<'PY'
import cv2

url = "http://192.168.0.205:8080/video"

cap = cv2.VideoCapture(url)

print("camera opened:", cap.isOpened())

ok, frame = cap.read()
print("read frame:", ok)
print("frame shape:", None if frame is None else frame.shape)

cap.release()
PY
```

Success example:

```text
camera opened: True
read frame: True
frame shape: (1080, 1920, 3)
```

If your camera URL is different, change:

```bash
camera_source:="http://YOUR_PHONE_IP:PORT/video"
```

Example:

```bash
roslaunch local_home_assistant home_assistant_camera_mediapipe.launch \
camera_source:="http://192.168.1.50:8080/video"
```

---

### 6.2 Test Local USB Camera

Check available video devices:

```bash
ls /dev/video*
```

Optional:

```bash
sudo apt install -y v4l-utils
v4l2-ctl --list-devices
```

Test camera index 0:

```bash
python - <<'PY'
import cv2

cap = cv2.VideoCapture(0)

print("camera opened:", cap.isOpened())

ok, frame = cap.read()
print("read frame:", ok)
print("frame shape:", None if frame is None else frame.shape)

cap.release()
PY
```

If camera index `0` works:

```bash
roslaunch local_home_assistant home_assistant_camera_mediapipe.launch \
camera_source:=0
```

If camera index `1` works:

```bash
roslaunch local_home_assistant home_assistant_camera_mediapipe.launch \
camera_source:=1
```

---

## 7. Microphone Device Testing

### 7.1 Check WSL PulseAudio Source

```bash
export PULSE_SERVER=unix:/mnt/wslg/PulseServer
pactl info
pactl list short sources
```

Expected WSLg source example:

```text
RDPSource
```

Set default source:

```bash
pactl set-default-source RDPSource
pactl info | grep "Default Source"
```

Expected:

```text
Default Source: RDPSource
```

---

### 7.2 Test Recording with arecord

```bash
arecord -D pulse -f S16_LE -r 44100 -c 1 -d 5 /tmp/test_mic.wav
aplay /tmp/test_mic.wav
```

If you can hear your voice, the microphone input is working.

---

### 7.3 Check Python Audio Devices

```bash
source ~/venvs/ROS_HOME_ASSISTANT/bin/activate

python - <<'PY'
import sounddevice as sd

print(sd.query_devices())
print("default device:", sd.default.device)

print("\nInput devices:")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] > 0:
        print(i, d["name"], "inputs=", d["max_input_channels"], "default_sr=", d["default_samplerate"])
PY
```

Example output:

```text
0 pulse, ALSA (32 in, 32 out)
1 default, ALSA (32 in, 32 out)
```

For this project in WSL, the stable microphone node uses `arecord`:

```bash
rosrun local_home_assistant vosk_asr_arecord_node.py \
_sample_rate:=44100 \
_audio_device:=pulse \
_chunk_size:=4096
```

If you are using native Linux with a hardware microphone, check devices:

```bash
arecord -l
```

Example hardware device:

```text
card 1: USB Audio, device 0
```

Then test:

```bash
arecord -D hw:1,0 -f S16_LE -r 44100 -c 1 -d 5 /tmp/test_mic.wav
```

If it works, launch ASR with:

```bash
rosrun local_home_assistant vosk_asr_arecord_node.py \
_sample_rate:=44100 \
_audio_device:=hw:1,0 \
_chunk_size:=4096
```

---

## 8. Useful ROS Debug Commands

Check active nodes:

```bash
rosnode list
```

Check recognized speech text:

```bash
rostopic echo /recognizer/output
```

Check raw gesture output:

```bash
rostopic echo /home_assistant/gesture_raw
```

Check final commands:

```bash
rostopic echo /home_assistant/command
```

Check home state:

```bash
rostopic echo /home_assistant/state
```

Check camera topic:

```bash
rostopic hz /usb_cam/image_raw
```

---

## 9. Clean Old ROS Processes

Before a new demo run, clean old ROS processes:

```bash
pkill -f roslaunch
pkill -f roscore
pkill -f rosmaster
pkill -f home_state_manager
pkill -f home_visualizer_node
pkill -f camera_stream_node
pkill -f mediapipe_gesture_node
pkill -f gesture_interpreter_node
pkill -f voice_command_node
pkill -f vosk_asr
```

---

## 10. Why MediaPipe Instead of YOLOv5?

This project originally considered YOLOv5 for gesture recognition, but the current working prototype uses MediaPipe Hands.

Reason:

- The target gestures are simple and rule-based.
- MediaPipe provides 21 hand landmarks.
- The system can infer finger count and open/fist states using geometric rules.
- No custom dataset or YOLO training is required for the current MVP.
- This keeps the system lightweight and suitable for edge hardware such as the Jupiter robot.

YOLOv5 is kept as an optional future extension for more complex gesture classes or comparative evaluation.

---

## 11. License

This project is released under the Apache-2.0 License.
