# --- minimal torchvision shim so Ultralytics won't use torchvision.ops.nms
import sys, types, torch
def _torch_nms_no_tv(boxes, scores, iou_thres):
    if boxes.numel() == 0: return boxes.new_zeros((0,), dtype=torch.long)
    scores, order = scores.sort(descending=True); boxes = boxes[order]
    keep=[]; x1,y1,x2,y2 = boxes[:,0],boxes[:,1],boxes[:,2],boxes[:,3]
    areas=(x2-x1).clamp(min=0)*(y2-y1).clamp(min=0)
    while order.numel()>0:
        i=order[0]; keep.append(i)
        if order.numel()==1: break
        xx1=x1[order[1:]].clamp(min=float(x1[i]))
        yy1=y1[order[1:]].clamp(min=float(y1[i]))
        xx2=x2[order[1:]].clamp(max=float(x2[i]))
        yy2=y2[order[1:]].clamp(max=float(y2[i]))
        inter=(xx2-xx1).clamp(min=0)*(yy2-yy1).clamp(min=0)
        iou=inter/(areas[i]+areas[order[1:]]-inter+1e-6)
        order=order[torch.where(iou<=iou_thres)[0]+1]
    return torch.stack(keep) if len(keep) else boxes.new_zeros((0,), dtype=torch.long)
try:
    import importlib.metadata as im
    try: tvv = im.version("torchvision")
    except im.PackageNotFoundError: tvv = "0.13.1"
    tv = types.ModuleType("torchvision"); tv.__version__ = tvv
    class _Ops: pass
    _ops=_Ops(); _ops.nms=_torch_nms_no_tv
    tv.ops=_ops; sys.modules["torchvision"]=tv
except Exception: pass
# --- end shim

import os, time, cv2, numpy as np, subprocess as sp
from ultralytics import YOLO

# URLs
RTSP_IN  = "rtsp://192.168.7.166:8554/live/cam"   # we force TCP in GST pipeline
RTSP_OUT = "rtsp://192.168.7.166:8554/live/det"

# Light settings (Nano CPU infer)
IMGSZ = 320
OUT_W, OUT_H = 480, 270
FPS = 10
CONF_THRES = 0.25
BITRATE = 800_000  # bps

MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")
DEVICE = "cpu"

# ---- GStreamer pipelines (HW decode + HW encode, low-latency)
GST_IN = (
    f"rtspsrc location={RTSP_IN} protocols=tcp latency=0 ! "
    "rtph264depay ! h264parse ! "
    "nvv4l2decoder disable-dpb=true ! "  # HW decode, low-latency
    "nvvidconv ! video/x-raw,format=BGRx ! "
    "videoconvert ! video/x-raw,format=BGR ! "
    "appsink drop=true max-buffers=1 sync=false"
)

GST_OUT = (
    f"appsrc is-live=true block=true format=time do-timestamp=true "
    f"caps=video/x-raw,format=BGR,width={OUT_W},height={OUT_H},framerate={FPS}/1 ! "
    "videoconvert ! video/x-raw,format=NV12 ! "
    "nvvidconv ! video/x-raw(memory:NVMM),format=NV12 ! "
    f"nvv4l2h264enc maxperf-enable=1 insert-sps-pps=true iframeinterval={FPS} "
    f"control-rate=1 preset-level=1 bitrate={BITRATE} ! "
    "h264parse config-interval=1 ! "
    f"rtspclientsink location={RTSP_OUT} protocols=tcp latency=0"
)

# ---- Open devices
cap = cv2.VideoCapture(GST_IN, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("ERROR: failed to open input via GStreamer"); raise SystemExit(1)

writer = cv2.VideoWriter(GST_OUT, cv2.CAP_GSTREAMER, 0, float(FPS), (OUT_W, OUT_H))
if not writer.isOpened():
    print("ERROR: failed to open RTSP writer via GStreamer"); raise SystemExit(1)

model = YOLO(MODEL_PATH)
names = model.names

def draw_boxes(frame, boxes, scores, classes):
    for (x1,y1,x2,y2), s, c in zip(boxes, scores, classes):
        x1,y1,x2,y2 = map(int,[x1,y1,x2,y2])
        cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
        label=f"{names[int(c)]} {float(s):.2f}"
        cv2.putText(frame,label,(x1,max(y1-5,10)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(10,10,10),2,cv2.LINE_AA)
        cv2.putText(frame,label,(x1,max(y1-5,10)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(240,240,240),1,cv2.LINE_AA)
    return frame

print("Running… Ctrl+C to stop.")
interval = 1.0/FPS; t0 = 0.0
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.02)  # brief backoff, appsink drops late frames
            continue

        frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)

        res = model.predict(frame, imgsz=IMGSZ, device=DEVICE, conf=CONF_THRES, verbose=False)[0]
        if res.boxes is not None and len(res.boxes) > 0:
            xyxy = res.boxes.xyxy.detach().cpu().numpy()
            conf = res.boxes.conf.detach().cpu().numpy()
            cls  = res.boxes.cls.detach().cpu().numpy()
            frame = draw_boxes(frame, xyxy, conf, cls)

        writer.write(frame)  # pushes into HW encoder

        now = time.time()
        slp = interval - (now - t0)
        if slp > 0: time.sleep(slp)
        t0 = time.time()
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    writer.release()
    print("Stopped.")
