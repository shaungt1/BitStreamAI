#!/usr/bin/env python3
# nano_yolo_ws.py — JetPack 4 + Python 3.8 venv, no GStreamer required
# Reads RTMP first (local), falls back to RTSP/TCP if needed. Tiny buffers. YOLOv8n CPU.

# ===== torchvision + metadata shim (avoid C++ ops requirement)
import sys, types, torch
import importlib.metadata as im
_real_version = im.version
def _fake_version(name):
    if name == "torchvision": return "0.13.1"
    return _real_version(name)
im.version = _fake_version

def _torch_nms_no_tv(boxes, scores, iou_thres):
    if boxes.numel() == 0:
        return boxes.new_zeros((0,), dtype=torch.long)
    scores, order = scores.sort(descending=True)
    x1,y1,x2,y2 = boxes[:,0],boxes[:,1],boxes[:,2],boxes[:,3]
    areas = (x2-x1).clamp(min=0)*(y2-y1).clamp(min=0)
    keep=[]
    while order.numel()>0:
        i=order[0]; keep.append(i)
        if order.numel()==1: break
        rest=order[1:]
        xx1=torch.maximum(x1[rest],x1[i]); yy1=torch.maximum(y1[rest],y1[i])
        xx2=torch.minimum(x2[rest],x2[i]); yy2=torch.minimum(y2[rest],y2[i])
        inter=(xx2-xx1).clamp(min=0)*(yy2-yy1).clamp(min=0)
        iou=inter/(areas[i]+areas[rest]-inter+1e-6)
        order=rest[torch.where(iou<=iou_thres)[0]]
    return torch.stack(keep) if keep else boxes.new_zeros((0,), dtype=torch.long)

tv = types.ModuleType("torchvision")
tv.__version__ = "0.13.1"
tv.ops = types.SimpleNamespace(nms=_torch_nms_no_tv)
sys.modules["torchvision"] = tv
# ===== end shim

# ===== app
import os, cv2, time, json, asyncio, websockets
from ultralytics import YOLO

try: torch.set_num_threads(1)
except Exception: pass

# ---- CONFIG (edit host if needed)
MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")
RTMP_URL   = "rtmp://127.0.0.1:1935/live/cam?live=1"
RTSP_LOCAL = "rtsp://127.0.0.1:8554/live/cam"
RTSP_LAN   = "rtsp://192.168.7.166:8554/live/cam"
WS_PORT    = 8765

# Force TCP + tiny/no buffers for FFmpeg (OpenCV backend)
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    "rtsp_transport;tcp|max_delay;0|buffer_size;102400|stimeout;2000000|"
    "analyzeduration;0|probesize;3200|fflags;nobuffer|flags;low_delay|"
    "reorder_queue_size;0|fpsprobesize;0"
)

# YOLO knobs for Nano 2GB
IMGSZ=256
CONF=0.25
TARGET_FPS=2

print(f"[init] loading model: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    raise SystemExit(f"model not found: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

def _open_ffmpeg(url: str) -> cv2.VideoCapture:
    print(f"[src] trying OpenCV/FFmpeg: {url}")
    cap = cv2.VideoCapture(url)
    if cap.isOpened():
        try: cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception: pass
        print("[src] opened")
        return cap
    print("[src] failed")
    return None

def open_capture() -> cv2.VideoCapture:
    # 1) Prefer the ORIGINAL RTMP you publish (bypasses the RTSP repack corruption)
    cap = _open_ffmpeg(RTMP_URL)
    if cap: return cap

    # 2) Fallback to RTSP on localhost, forced TCP
    cap = _open_ffmpeg(RTSP_LOCAL + "?rtsp_transport=tcp")
    if cap: return cap

    # 3) Fallback to RTSP on LAN IP, forced TCP
    cap = _open_ffmpeg(RTSP_LAN + "?rtsp_transport=tcp")
    if cap: return cap

    raise SystemExit("No video source opened (RTMP and RTSP/TCP all failed). Check publisher and MediaMTX.")

cap = open_capture()
last_infer = 0.0
clients=set()

async def ws_handler(ws, path):
    clients.add(ws)
    print(f"[ws] client connected ({len(clients)} total)")
    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        clients.discard(ws)
        print(f"[ws] client disconnected ({len(clients)} total)")

async def producer():
    global cap, last_infer
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[src] read failed, reopening in 0.5s…")
            await asyncio.sleep(0.5)
            try: cap.release()
            except Exception: pass
            cap = open_capture()
            continue

        now = time.time()
        if now - last_infer < 1.0 / max(TARGET_FPS, 0.5):
            await asyncio.sleep(0)
            continue
        last_infer = now

        r = model.predict(frame, imgsz=IMGSZ, device="cpu", conf=CONF, verbose=False)[0]
        H, W = frame.shape[:2]
        dets = []
        if getattr(r, "boxes", None) is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.cpu().numpy()
            cls  = r.boxes.cls.cpu().numpy().astype(int)
            conf = r.boxes.conf.cpu().numpy()
            for (x1,y1,x2,y2), c, p in zip(xyxy, cls, conf):
                dets.append({
                    "cls": int(c), "conf": float(p),
                    "x": float(x1/W), "y": float(y1/H),
                    "w": float((x2-x1)/W), "h": float((y2-y1)/H)
                })

        msg = json.dumps({"t": time.time(), "dets": dets, "w": W, "h": H})
        dead=[]
        for ws in list(clients):
            try:    await ws.send(msg)
            except Exception: dead.append(ws)
        for ws in dead: clients.discard(ws)
        await asyncio.sleep(0)

async def main():
    print(f"[ws] starting server on 0.0.0.0:{WS_PORT}")
    server = await websockets.serve(ws_handler, "0.0.0.0", WS_PORT, ping_interval=20, ping_timeout=20)
    try:    await producer()
    finally:
        server.close(); await server.wait_closed()

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
    print("exiting")
