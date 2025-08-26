# ~/BitStreamAI/edge/nano_yolov8_stream.py
import sys, types, torch
def _torch_nms_no_tv(boxes, scores, iou_thres):
    if boxes.numel()==0: return boxes.new_zeros((0,), dtype=torch.long)
    scores, order = scores.sort(descending=True); boxes = boxes[order]
    keep=[]; x1,y1,x2,y2 = boxes[:,0],boxes[:,1],boxes[:,2],boxes[:,3]
    areas=(x2-x1).clamp(min=0)*(y2-y1).clamp(min=0)
    while order.numel()>0:
        i=order[0]; keep.append(i)
        if order.numel()==1: break
        xx1=x1[order[1:]].clamp(min=float(x1[i])); yy1=y1[order[1:]].clamp(min=float(y1[i]))
        xx2=x2[order[1:]].clamp(max=float(x2[i])); yy2=y2[order[1:]].clamp(max=float(y2[i]))
        inter=(xx2-xx1).clamp(min=0)*(yy2-yy1).clamp(min=0)
        iou=inter/(areas[i]+areas[order[1:]]-inter+1e-6)
        order=order[torch.where(iou<=iou_thres)[0]+1]
    return torch.stack(keep) if len(keep) else boxes.new_zeros((0,), dtype=torch.long)
try:
    import importlib.metadata as im
    try: tvv=im.version("torchvision")
    except im.PackageNotFoundError: tvv="0.13.1"
    tv=types.ModuleType("torchvision"); tv.__version__=tvv
    class _Ops: pass
    tv.ops=_Ops(); tv.ops.nms=_torch_nms_no_tv
    sys.modules["torchvision"]=tv
except Exception: pass

import os, time, subprocess as sp, cv2, numpy as np
from ultralytics import YOLO

RTSP_IN  = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"
RTSP_OUT = "rtsp://192.168.7.166:8554/live/det"

IMGSZ=320; OUT_W,OUT_H=480,270; FPS=10; CONF=0.25; BITRATE=800000
DEVICE="cpu"
MODEL=os.path.expanduser("~/models/yolov8n.pt")
model=YOLO(MODEL); names=model.names

# Input via FFmpeg backend (tiny buffer, TCP)
cap=cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
if not cap.isOpened():
    print("ERROR: cannot open", RTSP_IN); sys.exit(1)

# HW encoder path using gst-launch (needs rtspclientsink installed)
def start_gst():
    cmd=[
        "gst-launch-1.0","-q",
        "fdsrc","fd=0","!","videoparse",
        f"width={OUT_W}",f"height={OUT_H}","format=bgr",f"framerate={FPS}/1",
        "!","videoconvert","!","video/x-raw,format=NV12",
        "!","nvvidconv","!","video/x-raw(memory:NVMM),format=NV12",
        "!","nvv4l2h264enc",f"bitrate={BITRATE}","maxperf-enable=1","insert-sps-pps=true",f"iframeinterval={FPS}",
        "control-rate=1","preset-level=1",
        "!","h264parse","config-interval=1",
        "!","rtspclientsink",f"location={RTSP_OUT}","protocols=tcp","latency=0"
    ]
    return sp.Popen(cmd, stdin=sp.PIPE)
w=start_gst()

def draw(f, b, s, c):
    for (x1,y1,x2,y2),sc,cl in zip(b,s,c):
        x1,y1,x2,y2=map(int,[x1,y1,x2,y2])
        cv2.rectangle(f,(x1,y1),(x2,y2),(0,255,0),2)
        lab=f"{names[int(cl)]} {float(sc):.2f}"
        cv2.putText(f,lab,(x1,max(y1-5,10)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,0,0),2)
        cv2.putText(f,lab,(x1,max(y1-5,10)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),1)

print("Running… Ctrl+C to stop.")
interval=1.0/FPS; t0=time.time()
try:
    while True:
        ok,frame=cap.read()
        if not ok: time.sleep(0.02); continue
        frame=cv2.resize(frame,(OUT_W,OUT_H),interpolation=cv2.INTER_LINEAR)

        r=model.predict(frame,imgsz=IMGSZ,device=DEVICE,conf=CONF,verbose=False)[0]
        if r.boxes is not None and len(r.boxes)>0:
            xyxy=r.boxes.xyxy.detach().cpu().numpy()
            conf=r.boxes.conf.detach().cpu().numpy()
            cls =r.boxes.cls.detach().cpu().numpy()
            draw(frame,xyxy,conf,cls)

        try:
            w.stdin.write(frame.tobytes())
        except BrokenPipeError:
            try: w.stdin.close()
            except: pass
            try: w.wait(timeout=1)
            except: pass
            w=start_gst()

        now=time.time(); slp=interval-(now-t0)
        if slp>0: time.sleep(slp)
        t0=time.time()
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    try: w.stdin.close()
    except: pass
    try: w.wait(timeout=2)
    except: pass
    print("Stopped.")
# Note: to view the output stream, use VLC or similar to open the URL rtsp://