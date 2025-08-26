import { StreamSource } from "@/types/stream"

export const defaultStreamSources: StreamSource[] = [
  {
    id: "edge01",
    label: "OR Camera 1", 
    url: "http://192.168.7.166:8889/live/cam/whep",
    description: "Primary surgical monitoring camera with AI detection capabilities",
    type: "main",
    protocol: "webrtc",
    transport: "whep",
    aiSources: ["yolov8", "llm"],
    aiSourcesCount: 2
  },
  {
    id: "edge02",
    label: "OR Camera 2",
    url: "http://192.168.7.166:8890/live/cam/whep", 
    description: "Secondary surgical monitoring camera for comprehensive coverage",
    type: "main",
    protocol: "webrtc",
    transport: "whep",
    aiSources: ["yolov8", "llm"],
    aiSourcesCount: 2
  }
]

export const streamSourceGroups = {
  main: defaultStreamSources.filter(s => s.type === 'main'),
  detection: defaultStreamSources.filter(s => s.type === 'detection'),
  custom: defaultStreamSources.filter(s => s.type === 'custom')
}

// Stream management functions
export const addStreamSource = (source: Omit<StreamSource, 'id'>): StreamSource => {
  return {
    ...source,
    id: `stream-${Date.now()}`
  }
}

export const saveStreamsToStorage = (streams: StreamSource[]) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('bitstreamAI-streams', JSON.stringify(streams))
  }
}

export const loadStreamsFromStorage = (): StreamSource[] => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('bitstreamAI-streams')
    if (saved) {
      return JSON.parse(saved)
    }
  }
  return defaultStreamSources
}