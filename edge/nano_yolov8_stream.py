# ---- TorchVision shim with built-in NMS (NO torchvision.ops needed)
# This creates a fake `torchvision.ops.nms` that uses a pure-PyTorch NMS.
import sys, types
import importlib
import importlib.metadata as im
import torch

def _torch_nms_no_tv(boxes, scores, iou_thres):
    """
    Pure-PyTorch NMS replacement matching torchvision.ops.nms signature.
    boxes: (N, 4) [x1,y1,x2,y2] tensor
    scores: (N,) tensor
    iou_thres: float
    returns: indices (LongTensor) of kept boxes
    """
    if boxes.numel() == 0:
        return boxes.new_zeros((0,), dtype=torch.long)
    # sort by score desc
    scores, order = scores.sort(descending=True)
    boxes = boxes[order]

    keep = []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1).clamp(min=0) * (y2 - y1).clamp(min=0)

    while order.numel() > 0:
        i = order[0]
        keep.append(i)

        if order.numel() == 1:
            break

        # compute IoU of the top box with the rest
        xx1 = x1[order[1:]].clamp(min=x1[i].item())
        yy1 = y1[order[1:]].clamp(min=y1[i].item())
        xx2 = x2[order[1:]].clamp(max=x2[i].item())
        yy2 = y2[order[1:]].clamp(max=y2[i].item())

        w = (xx2 - xx1).clamp(min=0)
        h = (yy2 - yy1).clamp(min=0)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)

        # keep boxes with IoU <= threshold
        remain = torch.nonzero(iou <= iou_thres).squeeze(1) + 1
        order = order[remain]

    # `keep` currently holds original indices from `order` space; convert to 1D tensor
    return torch.stack(keep) if len(keep) else boxes.new_zeros((0,), dtype=torch.long)

# Provide a minimal torchvision module with ops.nms pointing to our function
try:
    # if torchvision is installed, keep its version for Ultralytics metadata read
    tv_version = None
    try:
        tv_version = im.version("torchvision")
    except im.PackageNotFoundError:
        # fake a version so Ultralytics' metadata query succeeds
        tv_version = "0.13.1"

    tv = types.ModuleType("torchvision")
    tv.__version__ = tv_version
    class _Ops: pass
    _ops = _Ops()
    _ops.nms = _torch_nms_no_tv
    tv.ops = _ops

    # expose torchvision to import system
    sys.modules["torchvision"] = tv
except Exception:
    pass
# ---- end shim

import os
import subprocess as sp
import time
import cv2
import numpy as np
from ultralytics import YOLO

# ========= CONFIG =========
# Input (your existing CSI->MediaMTX stream)
RTSP_IN = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"

# Output (annotated stream back to MediaMTX; play via /live/det/whep)
RTMP_OUT = "rtmp://192.168.7.166:1935/live/det"

# Inference/encode params
IMGSZ = 640                   # YOLO inference size
OUT_W, OUT_H = 640, 360       # encoder output size to keep CPU light
FPS = 15
CONF_THRES = 0.25

# Model path (use your local weights)
MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")

# ========= SETUP =========
device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = YOLO(MODEL_PATH)

# Open input stream
cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print("❌ Failed to open RTSP:", RTSP_IN)
    sys.exit(1)

# FFmpeg process to push annotated frames to MediaMTX as RTMP
ffmpeg_cmd = [
    "ffmpeg",
    "-loglevel", "error",
    "-re",
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-s", f"{OUT_W}x{OUT_H}",
    "-r", str(FPS),
    "-i", "-",                  # stdin
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

print("✅ Starting detection stream... Press Ctrl+C to stop.")
try:
    frame_interval = 1.0 / FPS
    last_t = 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.1)
            continue

        frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)

        # Inference
        results = model.predict(frame, imgsz=IMGSZ, device=device, conf=CONF_THRES, verbose=False)
        r = results[0]
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.detach().to("cpu")
            conf = r.boxes.conf.detach().to("cpu")
            cls = r.boxes.cls.detach().to("cpu")
            frame = draw_boxes(frame, xyxy.numpy(), conf.numpy(), cls.numpy())

        # simple FPS pacing
        now = time.time()
        sleep = frame_interval - (now - last_t)
        if sleep > 0:
            time.sleep(sleep)
        last_t = time.time()

        # Write to ffmpeg
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
