# ---- torchvision + metadata shim (JetPack 4 safe)
import sys, types, torch
import importlib.metadata as im

# 1) Fake a torchvision version so Ultralytics import stops crashing
_real_version = im.version
def _fake_version(name):
    if name == "torchvision":
        return "0.13.1"
    return _real_version(name)
im.version = _fake_version

# 2) Provide a minimal torchvision with ops.nms implemented in pure torch
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
# ---- end shim

# ---- actual app
import os, cv2, time, json, asyncio, websockets
from ultralytics import YOLO

MODEL_PATH = os.path.expanduser("~/models/yolov8n.pt")
RTSP_IN    = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"
IMGSZ      = 256
CONF       = 0.25
TARGET_FPS = 2
WS_PORT    = 8765

print(f"[init] loading model: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    raise SystemExit(f"model not found: {MODEL_PATH}")
model = YOLO(MODEL_PATH)

print(f"[init] opening rtsp: {RTSP_IN}")
cap = cv2.VideoCapture(RTSP_IN)
if not cap.isOpened():
    raise SystemExit(f"could not open RTSP: {RTSP_IN}")

last = 0.0
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
    global last
    while True:
        ok, frame = cap.read()
        if not ok:
            print("[rtsp] read failed, retrying in 0.5s...")
            await asyncio.sleep(0.5)
            cap.open(RTSP_IN)
            continue
        now = time.time()
        if now - last < 1.0 / max(TARGET_FPS, 0.5):
            await asyncio.sleep(0)
            continue
        last = now

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