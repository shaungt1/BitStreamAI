export interface StreamSource {
  id: string
  label: string
  url: string
  description?: string
  type: 'main' | 'detection' | 'custom'
  protocol: 'webrtc' | 'rtmp' | 'hls'
  transport: 'whep' | 'udp' | 'tcp'
  aiSources?: string[]
  aiSourcesCount?: number
}

export interface StreamPlayerConfig {
  sources: StreamSource[]
  defaultSourceId?: string
}