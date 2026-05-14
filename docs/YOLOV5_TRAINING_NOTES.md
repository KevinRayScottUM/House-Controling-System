# YOLOv5n Gesture Training Notes

The first runnable prototype uses MediaPipe because it works without a custom dataset.
YOLOv5n is recommended as the second-stage deployable model after you collect and label your own gesture images.

Gesture classes:

```text
left_1
left_2
left_3
right_open
right_fist
```

A normal pretrained COCO YOLOv5n model does not know these hand gesture classes. Use `yolov5n.pt` only as a lightweight base checkpoint.

## Download YOLOv5 and base model

```bash
cd ~/catkin_ws/src/local_home_assistant
mkdir -p third_party models dataset/gesture_yolo/images/train dataset/gesture_yolo/images/val dataset/gesture_yolo/labels/train dataset/gesture_yolo/labels/val
cd third_party
git clone https://github.com/ultralytics/yolov5.git
cd yolov5
python3 -m pip install -r requirements.txt
wget -O yolov5n.pt https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.pt
```

## Dataset yaml

Create `dataset/gesture_yolo/gesture.yaml`:

```yaml
path: /home/ros/catkin_ws/src/local_home_assistant/dataset/gesture_yolo
train: images/train
val: images/val
names:
  0: left_1
  1: left_2
  2: left_3
  3: right_open
  4: right_fist
```

## Train

```bash
cd ~/catkin_ws/src/local_home_assistant/third_party/yolov5
python3 train.py --img 320 --batch 16 --epochs 50 --data ../dataset/gesture_yolo/gesture.yaml --weights yolov5n.pt --name home_gesture_yolov5n
```

## Export ONNX

```bash
python3 export.py --weights runs/train/home_gesture_yolov5n/weights/best.pt --include onnx --img 320
cp runs/train/home_gesture_yolov5n/weights/best.onnx ../../models/gesture_yolov5n.onnx
```
