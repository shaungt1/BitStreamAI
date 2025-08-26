#!/usr/bin/env python3
# edge.nano_yolo_ws.py

# ===== torchvision + metadata shim (JetPack 4 safe)
import sys, types, torch
import importlib.metadata as im

_real_version = im.version
def _fake_version(name):
    if name == "torchvision":
        return "0.13.1"
    return _real_version(name)
im.version = _fake_version

def _torch_nms_no_tv(boxes, scores, iou_thres):
    if boxes.numel() == 0:
        return boxes.new_zeros((0,), dtype=torch.long)
    scores, order = scores.sort(descending=True)
    x1,y1,x2,y2 = boxes[:,0],boxes[:,1],boxes[:,2],boxes[:,3]
    areas = (x2-x1).clamp(min=0)*(y2-y1).clamp(min=0)
    keep=[]
    while order.numel() > 0:
        i = order[0]
        keep.append(i)
        if order.numel() == 1: break
        rest = order[1:]
        xx1 = torch.maximum(x1[rest], x1[i])
        yy1 = torch.maximum(y1[rest], y1[i])
        xx2 = torch.minimum(x2[rest], x2[i])
        yy2 = torch.minimum(y2[rest], y2[i])
        inter = (xx2-xx1).clamp(min=0)*(yy2-yy1).clamp(min=0)
        iou = inter / (areas[i] + areas[rest] - inter + 1e-6)
        order = rest[torch.where(iou <= iou_thres)[0]]
    return torch.stack(keep) if keep else boxes.new_zeros((0,), dtype=torch.long)

tv = types.ModuleType("torchvision")
tv.__dict__["__version__"] = "0.13.1"
ops = types.SimpleNamespace(nms=_torch_nms_no_tv)
tv.__dict__["ops"] = ops
sys.modules["torchvision"] = tv
# ===== end shim

# ===== app
import os, cv2, time, json, asyncio, websockets
from ultralytics import YOLO

# ---- CONFIG (edit RTSP_IN if your path/port differs)
MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")
RTSP_IN    = "rtsp://192.168.7.166:8554/live/cam"  # NOTE: no ?rtsp_transport=tcp here
WS_PORT    = 8765
IMGSZ      = 256
CONF       = 0.25
TARGET_FPS = 2
GST_LAT    = 200  # ms

try:
    torch.set_num_threads(1)
except Exception:
    pass

print(f"[init] loading model: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    raise SystemExit(f"model not found: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

def gst_pipe_hw(rtsp:str)->str:
    # HW decode path (Jetson): nvv4l2decoder
    return (
        f'rtspsrc location="{rtsp}" protocols=tcp latency={GST_LAT} drop-on-latency=true ! '
        'rtph264depay ! h264parse ! '
        'nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx ! '
        'videoconvert ! video/x-raw,format=BGR ! '
        'appsink sync=false max-buffers=1 drop=true'
    )

def gst_pipe_decodebin(rtsp:str)->str:
    # Auto-decoder (lets GStreamer pick available decoder)
    return (
        f'rtspsrc location="{rtsp}" protocols=tcp latency={GST_LAT} drop-on-latency=true ! '
        'rtph264depay ! h264parse ! decodebin ! '
        'videoconvert ! video/x-raw,format=BGR ! '
        'appsink sync=false max-buffers=1 drop=true'
    )

def gst_pipe_sw(rtsp:str)->str:
    # Software decode explicitly with avdec_h264
    return (
        f'rtspsrc location="{rtsp}" protocols=tcp latency={GST_LAT} drop-on-latency=true ! '
        'rtph264depay ! h264parse ! '
        'avdec_h264 ! videoconvert ! video/x-raw,format=BGR ! '
        'appsink sync=false max-buffers=1 drop=true'
    )

def open_capture():
    # Try multiple pipelines in order; print why it failed
    tries = [
        ("GStreamer HW (nvv4l2decoder)", gst_pipe_hw(RTSP_IN)),
        ("GStreamer decodebin (auto)",   gst_pipe_decodebin(RTSP_IN)),
        ("GStreamer SW (avdec_h264)",    gst_pipe_sw(RTSP_IN)),
        ("OpenCV FFmpeg fallback",       None),
    ]
    # Check if OpenCV has GStreamer built-in
    has_gst = "GStreamer" in cv2.getBuildInformation()

    for name, pipe in tries:
        if "GStreamer" in name and not has_gst:
            print(f"[rtsp] skipping {name}: OpenCV GStreamer support not built")
            continue
        if pipe is None:
            print(f"[rtsp] trying {name}: {RTSP_IN}")
            cap = cv2.VideoCapture(RTSP_IN)  # FFmpeg fallback
        else:
            print(f"[rtsp] trying {name}")
            cap = cv2.VideoCapture(pipe, cv2.CAP_GSTREAMER)

        if cap.isOpened():
            print(f"[rtsp] capture opened via {name}")
            return cap
        else:
            print(f"[rtsp] {name} failed")

    raise SystemExit("could not open RTSP with any method. Check plugins and RTSP URL.")

cap = open_capture()
last_infer = 0.0
clients = set()

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
            print("[rtsp] read failed, reopening in 0.5s…")
            await asyncio.sleep(0.5)
            try:
                cap.release()
            except Exception:
                pass
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
            try:
                await ws.send(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            clients.discard(ws)
        await asyncio.sleep(0)

async def main():
    print(f"[ws] starting server on 0.0.0.0:{WS_PORT}")
    server = await websockets.serve(ws_handler, "0.0.0.0", WS_PORT, ping_interval=20, ping_timeout=20)
    try:
        await producer()
    finally:
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("FATAL:", e)