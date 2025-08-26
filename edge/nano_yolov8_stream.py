import os
import sys
import subprocess as sp
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# CONFIG
RTSP_IN = "rtsp://192.168.7.166:8554/live/cam"      # your existing camera stream from MediaMTX
RTMP_OUT = "rtmp://192.168.7.166:1935/live/det"     # annotated stream back to MediaMTX
IMGSZ = 640                                         # inference size
OUT_W, OUT_H = 640, 360                             # output stream size to keep CPU load low
FPS = 15                                            # lower if Nano struggles
CONF_THRES = 0.25

# Model load (pretrained small model)
device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8n.pt")  # Ultralytics will download if not present

# Open input stream (via OpenCV + FFMPEG)
cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print("Failed to open input RTSP. Check MediaMTX RTSP and path.")
    sys.exit(1)

# Prepare ffmpeg process to push annotated frames to MediaMTX as RTMP
ffmpeg_cmd = [
    "ffmpeg",
    "-loglevel", "error",
    "-re",
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{OUT_W}x{OUT_H}",
    "-r", str(FPS),
    "-i", "-",                         # stdin
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
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 2, cv2.LINE_AA)
        cv2.putText(frame, label, (x1, max(y1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1, cv2.LINE_AA)
    return frame

# Warmup a blank frame to compile kernels
dummy = np.zeros((OUT_H, OUT_W, 3), dtype=np.uint8)
_ = model.predict(dummy, imgsz=IMGSZ, device=device, verbose=False)

print("Running. Press Ctrl+C to stop.")
try:
    frame_interval = 1.0 / FPS
    last_t = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            # brief backoff and retry
            time.sleep(0.1)
            continue

        # Resize for speed and consistent encoder input
        frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)

        # Inference
        results = model.predict(frame, imgsz=IMGSZ, device=device, conf=CONF_THRES, verbose=False)
        r = results[0]
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.detach().cpu().numpy()
            conf = r.boxes.conf.detach().cpu().numpy()
            cls = r.boxes.cls.detach().cpu().numpy()
            frame = draw_boxes(frame, xyxy, conf, cls)

        # Rate control
        now = time.time()
        sleep = frame_interval - (now - last_t)
        if sleep > 0:
            time.sleep(sleep)
        last_t = time.time()

        # Write to ffmpeg stdin
        try:
            ffmpeg.stdin.write(frame.tobytes())
        except BrokenPipeError:
            print("FFmpeg pipe closed. Exiting.")
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
    print("Stopped.")
