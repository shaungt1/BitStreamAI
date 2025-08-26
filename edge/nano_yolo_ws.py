#!/usr/bin/env python3
# YOLO → WebSocket JSON overlay server (no re-encode, lowest latency)
# - RTSP input via OpenCV/FFmpeg (TCP, tiny buffer, auto-reconnect)
# - Ultralytics YOLO on CPU
# - Pure-PyTorch NMS shim so torchvision C++ ops are NOT required
# - Sends normalized boxes over WS; browser draws overlay

# ----- TorchVision shim (provide ops.nms without C++ extension)
import sys, types, torch
def _nms_torch_only(boxes, scores, iou_thres):
    # boxes: (N,4) xyxy; scores: (N,)
    if boxes.numel() == 0:
        return boxes.new_zeros((0,), dtype=torch.long)
    scores, order = scores.sort(descending=True)
    boxes = boxes[order]
    keep = []
    x1,y1,x2,y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
    areas = (x2 - x1).clamp(min=0) * (y2 - y1).clamp(min=0)
    while order.numel() > 0:
        i = order[0]
        keep.append(i)
        if order.numel() == 1:
            break
        xx1 = torch.maximum(x1[order[1:]], x1[i])
        yy1 = torch.maximum(y1[order[1:]], y1[i])
        xx2 = torch.minimum(x2[order[1:]], x2[i])
        yy2 = torch.minimum(y2[order[1:]], y2[i])
        inter = (xx2 - xx1).clamp(min=0) * (yy2 - yy1).clamp(min=0)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
        remain = torch.nonzero(iou <= iou_thres).squeeze(1) + 1
        order = order[remain]
    return torch.stack(keep) if keep else boxes.new_zeros((0,), dtype=torch.long)

try:
    import importlib.metadata as im
    # Pretend a friendly torchvision version to silence compatibility warnings
    try: tvv = im.version("torchvision")
    except im.PackageNotFoundError: tvv = "0.19.0"
    tv = types.ModuleType("torchvision"); tv.__version__ = tvv
    class _Ops: pass
    _ops = _Ops(); _ops.nms = _nms_torch_only
    tv.ops = _ops
    sys.modules["torchvision"] = tv
except Exception:
    pass
# ----- end shim

import os, cv2, time, asyncio, json, numpy as np
from ultralytics import YOLO
import websockets

# ---- config
RTSP_IN = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"
WS_HOST = "0.0.0.0"
WS_PORT = 8765

IMGSZ = 320          # smaller = faster on CPU
CONF  = 0.25
TARGET_INFER_FPS = 3 # run YOLO ~3Hz; keep reading frames at camera rate to avoid lag

MODEL = os.path.expanduser("~/models/yolov8n.pt")
DEVICE = "cpu"       # your Torch has no CUDA visible right now

# ---- model
model = YOLO(MODEL)
names = model.names

# ---- capture with small buffer + auto-reconnect
def open_cap():
    cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap

cap = open_cap()
if not cap.isOpened():
    print(f"[ERR] cannot open {RTSP_IN} (is MediaMTX + /live/cam up?)")

clients = set()

async def producer():
    global cap
    last_infer = 0.0
    bad_reads = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            bad_reads += 1
            if bad_reads >= 25:
                # re-open input after ~25 failed grabs
                try: cap.release()
                except: pass
                time.sleep(0.2)
                cap = open_cap()
                bad_reads = 0
            await asyncio.sleep(0.02)
            continue

        bad_reads = 0
        h, w = frame.shape[:2]

        # throttle inference to avoid CPU backlog
        now = time.time()
        if now - last_infer < (1.0 / max(TARGET_INFER_FPS, 0.5)):
            await asyncio.sleep(0)  # yield to WS loop
            continue
        last_infer = now

        # run YOLO
        r = model.predict(
            frame, imgsz=IMGSZ, device=DEVICE, conf=CONF, verbose=False
        )[0]

        detections = []
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.detach().cpu().numpy()
            conf = r.boxes.conf.detach().cpu().numpy()
