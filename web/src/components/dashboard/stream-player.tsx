"use client"

import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, Play, Square, RotateCcw } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface StreamPlayerProps {
  streamUrl?: string
  className?: string
  title?: string
}

export function StreamPlayer({ 
  streamUrl = "http://192.168.7.166:8889/live/det/whep",
  className,
  title = "CSI Camera Stream"
}: StreamPlayerProps) {
  const videoRef = React.useRef<HTMLVideoElement>(null)
  const pcRef = React.useRef<RTCPeerConnection | null>(null)
  const [isConnecting, setIsConnecting] = React.useState(false)
  const [isConnected, setIsConnected] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [latency, setLatency] = React.useState<number | null>(null)
  // inside your StreamPlayer component:
  const canvasRef = React.useRef<HTMLCanvasElement>(null);


  
  React.useEffect(() => {
    let ws: WebSocket | null = null;
    function draw(boxes: any[]) {
      const v = videoRef.current, c = canvasRef.current;
      if (!v || !c) return;
      c.width = v.clientWidth; c.height = v.clientHeight;
      const ctx = c.getContext("2d"); if (!ctx) return;
      ctx.clearRect(0,0,c.width,c.height);
      boxes.forEach(b => {
        const x1 = b.x1 * c.width, y1 = b.y1 * c.height;
        const x2 = b.x2 * c.width, y2 = b.y2 * c.height;
        ctx.strokeStyle = "lime"; ctx.lineWidth = 2;
        ctx.strokeRect(x1,y1,x2-x1,y2-y1);
        ctx.font = "12px sans-serif"; ctx.fillStyle = "white";
        ctx.strokeStyle = "black"; ctx.lineWidth = 3;
        const txt = `${b.label} ${b.conf.toFixed(2)}`;
        ctx.strokeText(txt, x1+3, y1-3); ctx.fillText(txt, x1+3, y1-3);
      });
    }
    ws = new WebSocket("ws://192.168.7.166:8765");
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      draw(msg.detections || []);
    };
    return () => { if (ws) ws.close(); };
  }, []);



  const connect = React.useCallback(async () => {
    if (!videoRef.current) return

    setIsConnecting(true)
    setError(null)

    try {
      const pc = new RTCPeerConnection()
      pcRef.current = pc

      // Ask for incoming media
      pc.addTransceiver('video', { direction: 'recvonly' })
      pc.addTransceiver('audio', { direction: 'recvonly' })

      pc.ontrack = (ev) => {
        if (videoRef.current) {
          videoRef.current.srcObject = ev.streams[0]
          setIsConnected(true)
          setIsConnecting(false)
        }
      }

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
          setIsConnected(false)
          setError('Connection lost')
        }
      }

      const offer = await pc.createOffer()
      await pc.setLocalDescription(offer)

      // Wait until ICE gathering completes
      await new Promise<void>((resolve) => {
        if (pc.iceGatheringState === 'complete') return resolve()
        pc.addEventListener('icegatheringstatechange', () => {
          if (pc.iceGatheringState === 'complete') resolve()
        })
      })

      const sdp = pc.localDescription?.sdp
      if (!sdp) throw new Error('Failed to create SDP')

      const startTime = Date.now()

      // Try path-style first, then query-style
      let resp = await fetch(streamUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp' },
        body: sdp
      })

      if (!resp.ok) {
        const fallbackUrl = streamUrl.replace('/live/cam/whep', '/whep?path=live/cam')
        resp = await fetch(fallbackUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: sdp
        })
      }

      if (!resp.ok) {
        throw new Error(`HTTP error! status: ${resp.status}`)
      }

      const answerSdp = await resp.text()
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })

      const connectionTime = Date.now() - startTime
      setLatency(connectionTime)

    } catch (err) {
      setIsConnecting(false)
      setIsConnected(false)
      setError(err instanceof Error ? err.message : 'Connection failed')
      console.error('WebRTC connection failed:', err)
    }
  }, [streamUrl])

  const disconnect = React.useCallback(() => {
    if (pcRef.current) {
      pcRef.current.close()
      pcRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsConnected(false)
    setIsConnecting(false)
    setError(null)
    setLatency(null)
  }, [])

  const reconnect = React.useCallback(() => {
    disconnect()
    setTimeout(connect, 1000)
  }, [disconnect, connect])

  React.useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">{title}</CardTitle>
        <div className="flex items-center space-x-2">
          {latency && (
            <Badge variant="outline" className="text-xs">
              {latency}ms
            </Badge>
          )}
          <Badge 
            variant={isConnected ? "default" : error ? "destructive" : "secondary"}
            className="text-xs"
          >
            {isConnected ? "Connected" : error ? "Error" : "Disconnected"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Video Player */}
        <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
          {isConnecting && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Skeleton className="w-full h-full" />
              <div className="absolute text-white">Connecting...</div>
            </div>
          )}
          
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            controls
            className="w-full h-full object-contain"
            style={{ display: isConnected ? 'block' : 'none' }}
          />
         <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />
          {!isConnected && !isConnecting && (
            <div className="absolute inset-0 flex items-center justify-center text-white">
              <div className="text-center">
                <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
                <p className="text-sm text-gray-400">No video stream</p>
              </div>
            </div>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Controls */}
        <div className="flex items-center space-x-2">
          {!isConnected && !isConnecting && (
            <Button onClick={connect} size="sm">
              <Play className="h-4 w-4 mr-2" />
              Connect
            </Button>
          )}
          
          {isConnected && (
            <Button onClick={disconnect} size="sm" variant="outline">
              <Square className="h-4 w-4 mr-2" />
              Disconnect
            </Button>
          )}
          
          <Button onClick={reconnect} size="sm" variant="outline">
            <RotateCcw className="h-4 w-4 mr-2" />
            Reconnect
          </Button>
        </div>

        {/* Stream Info */}
        <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
          <div>
            <span className="font-medium">Protocol:</span> WebRTC
          </div>
          <div>
            <span className="font-medium">Transport:</span> WHEP
          </div>
        </div>

        {/* AI Sources */}
        {(streamUrl === "http://192.168.7.166:8889/live/cam/whep" || streamUrl === "http://192.168.7.166:8890/live/cam/whep") && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-muted-foreground">AI Sources</div>
            <div className="flex items-center space-x-2">
              <Button 
                variant="outline" 
                size="sm" 
                className="bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
              >
                YOLOv8
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                className="bg-purple-50 border-purple-200 text-purple-700 hover:bg-purple-100"
              >
                LLM
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}