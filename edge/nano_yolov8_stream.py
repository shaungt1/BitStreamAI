# # CONFIG
# RTSP_IN = "rtsp://192.168.7.166:8554/live/cam"      # your existing camera stream from MediaMTX
# RTMP_OUT = "rtmp://192.168.7.166:1935/live/det"     # annotated stream back to MediaMTX


import os
import sys
import subprocess as sp
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# INPUT (from MediaMTX CSI camera stream)
RTSP_IN = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"

# OUTPUT (to MediaMTX as RTMP, will appear at /live/det)
RTMP_OUT = "rtmp://192.168.7.166:1935/live/det"

# Params
IMGSZ = 640
OUT_W, OUT_H = 640, 360
FPS = 15
CONF_THRES = 0.25

# Load YOLO model from your models folder
MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")
device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = YOLO(MODEL_PATH)

# Open input RTSP stream
cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print("❌ Failed to open RTSP stream:", RTSP_IN)
    sys.exit(1)

# Prepare FFmpeg pipeline for RTMP push
ffmpeg_cmd = [
    "ffmpeg",
    "-loglevel", "error",
    "-re",
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{OUT_W}x{OUT_H}",
    "-r", str(FPS),
    "-i", "-",  # stdin
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-tune", "zerolatency",
    "-g", str(FPS * 2),
    "-f", "flv",
    RTMP_OUT
]
ffmpeg = sp.Popen(ffmpeg_cmd, stdin=sp.PIPE)

names = model.names

def draw_boxes(frame, boxes, scores, classes):
    for (x1, y1, x2, y2), s, c in zip(boxes, scores, classes):
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{names[int(c)]} {float(s):.2f}"
        cv2.putText(frame, label, (x1, max(y1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 2)
        cv2.putText(frame, label, (x1, max(y1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1)
    return frame

print("✅ Starting detection stream... Press Ctrl+C to stop.")
try:
    frame_interval = 1.0 / FPS
    last_t = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.1)
            continue

        frame = cv2.resize(frame, (OUT_W, OUT_H))

        results = model.predict(frame, imgsz=IMGSZ, device=device, conf=CONF_THRES, verbose=False)
        r = results[0]
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.detach().cpu().numpy()
            conf = r.boxes.conf.detach().cpu().numpy()
            cls = r.boxes.cls.detach().cpu().numpy()
            frame = draw_boxes(frame, xyxy, conf, cls)

        # Control FPS
        now = time.time()
        sleep = frame_interval - (now - last_t)
        if sleep > 0:
            time.sleep(sleep)
        last_t = time.time()

        # Send frame to ffmpeg
        try:
            ffmpeg.stdin.write(frame.tobytes())
        except BrokenPipeError:
            print("❌ FFmpeg pipe closed. Exiting.")
            break

except KeyboardInterrupt:
    pass
finally:
    cap.release()
    try:
        ffmpeg.stdin.close()
    except Exception:
        pass
    ffmpeg.wait(timeout=2)
    print("🛑 Stopped.")
