# CPU YOLO + JSON over WebSocket; NO re-encode
import os, cv2, time, asyncio, json, numpy as np
from ultralytics import YOLO
import websockets

RTSP_IN = "rtsp://192.168.7.166:8554/live/cam?rtsp_transport=tcp"
IMGSZ = 320
CONF = 0.25
MODEL = os.path.expanduser("~/models/yolov8n.pt")

model = YOLO(MODEL)
names = model.names

cap = cv2.VideoCapture(RTSP_IN, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
if not cap.isOpened():
    raise SystemExit(f"cannot open {RTSP_IN}")

clients = set()

async def producer():
    while True:
        ok, frame = cap.read()
        if not ok:
            await asyncio.sleep(0.02); continue
        h, w = frame.shape[:2]
        r = model.predict(frame, imgsz=IMGSZ, device="cpu", conf=CONF, verbose=False)[0]
        detections = []
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.cpu().numpy()
            conf = r.boxes.conf.cpu().numpy()
            cls  = r.boxes.cls.cpu().numpy()
            for (x1,y1,x2,y2), s, c in zip(xyxy, conf, cls):
                detections.append({
                    "cls": int(c),
                    "label": names[int(c)],
                    "conf": float(s),
                    # normalized coords [0..1]
                    "x1": float(x1 / w), "y1": float(y1 / h),
                    "x2": float(x2 / w), "y2": float(y2 / h),
                })
        if clients and detections:
            msg = json.dumps({"t": time.time(), "w": w, "h": h, "detections": detections})
            await asyncio.gather(*(ws.send(msg) for ws in list(clients)))
        await asyncio.sleep(0)  # yield

async def handler(ws, _):
    clients.add(ws)
    try:
        await ws.wait_closed()
    finally:
        clients.discard(ws)

async def main():
    prod = asyncio.create_task(producer())
    async with websockets.serve(handler, "0.0.0.0", 8765, max_size=1_000_000):
        await prod

if __name__ == "__main__":
    asyncio.run(main())
