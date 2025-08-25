Open http://192.168.7.166:8889/live/cam in the browser. If that works, MediaMTX WebRTC is up.

Keep your RTMP pipeline running. Path must be live/cam.

Your custom WebRTC player will be blank if the PeerConnection does not ask for media and it likely posted the offer before ICE finished. Use this minimal WHEP player that:

1. requests recvonly video/audio
2. waits for ICE to complete (no trickle)
3. tries both path styles MediaMTX accepts