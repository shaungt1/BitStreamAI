# ---- minimal torchvision shim (no torchvision.ops needed)
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
# ---- end shim

import os, time, subprocess as sp
import cv2, numpy as np
from ultralytics import YOLO

RTSP_IN  = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"
RTSP_OUT = "rtsp://192.168.7.166:8554/live/det"

# Light CPU settings
IMGSZ = 320
OUT_W, OUT_H = 480, 270
FPS = 10
CONF_THRES = 0.25
BITRATE = 800000  # bps

MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")
DEVICE = "cpu"

def start_gst_writer():
    # We feed raw BGR frames on stdin to gst-launch (fdsrc) -> HW encoder -> RTSP
    cmd = [
        "gst-launch-1.0", "-q",
        "fdsrc", "fd=0",
        "!", "videoparse",
            f"width={OUT_W}", f"height={OUT_H}", "format=bgr", f"framerate={FPS}/1",
        "!", "videoconvert",
        "!", "video/x-raw,format=NV12",
        "!", "nvvidconv",
        "!", "video/x-raw(memory:NVMM),format=NV12",
        "!", "nvv4l2h264enc",
            "maxperf-enable=1", "insert-sps-pps=true", f"iframeinterval={FPS}",
            "control-rate=1", "preset-level=1", f"bitrate={BITRATE}",
        "!", "h264parse", "config-interval=1",
        "!", "rtspclientsink", f"location={RTSP_OUT}", "protocols=tcp", "latency=0"
    ]
    return sp.Popen(cmd, stdin=sp.PIPE)

# Input via FFmpeg backend; tiny buffer
cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
if not cap.isOpened():
    print("ERROR: cannot open", RTSP_IN); raise SystemExit(1)

writer = start_gst_writer()
model = YOLO(MODEL_PATH); names = model.names

def draw(frame, xyxy, conf, cls):
    for (x1,y1,x2,y2), s, c in zip(xyxy, conf, cls):
        x1,y1,x2,y2 = map(int,[x1,y1,x2,y2])
        cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
        label=f"{names[int(c)]} {float(s):.2f}"
        cv2.putText(frame,label,(x1,max(y1-5,10)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(10,10,10),2,cv2.LINE_AA)
        cv2.putText(frame,label,(x1,max(y1-5,10)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(240,240,240),1,cv2.LINE_AA)

print("Running… Ctrl+C to stop. Output: HW encoder via GStreamer")
interval = 1.0/FPS; t0 = time.time()
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.02); continue

        frame = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR)

        r = model.predict(frame, imgsz=IMGSZ, device=DEVICE, conf=CONF_THRES, verbose=False)[0]
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.detach().cpu().numpy()
            conf = r.boxes.conf.detach().cpu().numpy()
            cls  = r.boxes.cls.detach().cpu().numpy()
            draw(frame, xyxy, conf, cls)

        # Write to gst pipeline; if it dies, restart it
        try:
            writer.stdin.write(frame.tobytes())
        except BrokenPipeError:
            try: writer.stdin.close()
            except Exception: pass
            try: writer.wait(timeout=1)
            except Exception: pass
            writer = start_gst_writer()

        # pacing
        now = time.time(); slp = interval - (now - t0)
        if slp > 0: time.sleep(slp)
        t0 = time.time()
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    try: writer.stdin.close()
    except Exception: pass
    try: writer.wait(timeout=2)
    except Exception: pass
    print("Stopped.")
