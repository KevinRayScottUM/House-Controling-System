#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect raw images for YOLO gesture labeling.
Usage examples:
  python3 collect_gesture_dataset.py --label left_1 --source 0
  python3 collect_gesture_dataset.py --label right_open --source http://PHONE_IP:8080/video
Press SPACE to save one frame, A for auto-save toggle, Q to quit.
"""
import argparse, time
from pathlib import Path
import cv2
VALID={'left_1','left_2','left_3','right_open','right_fist'}
def parse_source(s): return int(s) if str(s).isdigit() else s
parser=argparse.ArgumentParser(); parser.add_argument('--label',required=True); parser.add_argument('--source',default='0'); parser.add_argument('--out',default='dataset/raw_images'); parser.add_argument('--interval',type=float,default=0.25)
args=parser.parse_args(); assert args.label in VALID, f'label must be one of {VALID}'
out=Path(args.out)/args.label; out.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(parse_source(args.source)); auto=False; last=0; count=len(list(out.glob('*.jpg')))
while True:
    ok,frame=cap.read()
    if not ok: print('failed to read frame'); time.sleep(.2); continue
    cv2.putText(frame,f'label={args.label} count={count} SPACE save A auto={auto} Q quit',(20,35),cv2.FONT_HERSHEY_SIMPLEX,.75,(0,255,0),2)
    now=time.time()
    if auto and now-last>=args.interval:
        cv2.imwrite(str(out/f'{args.label}_{count:05d}.jpg'),frame); count+=1; last=now
    cv2.imshow('collect_gesture_dataset',frame)
    key=cv2.waitKey(1)&0xFF
    if key==ord('q'): break
    if key==ord('a'): auto=not auto
    if key==32:
        cv2.imwrite(str(out/f'{args.label}_{count:05d}.jpg'),frame); count+=1
cap.release(); cv2.destroyAllWindows()
