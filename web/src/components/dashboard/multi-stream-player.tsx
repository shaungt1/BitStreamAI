"use client"

import * as React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { StreamPlayer } from "@/components/dashboard/stream-player"
import { StreamSource } from "@/types/stream"
import { Video, Eye, Plus, X } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface MultiStreamPlayerProps {
  className?: string
  sources?: StreamSource[]
  defaultActiveId?: string
  showAddButton?: boolean
  maxTabs?: number
}

export function MultiStreamPlayer({
  className,
  sources,
  defaultActiveId,
  showAddButton = true,
  maxTabs = 6
}: MultiStreamPlayerProps) {
  // Get streams from localStorage
  const [availableStreams, setAvailableStreams] = React.useState<StreamSource[]>([])
  
  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('bitstreamAI-streams')
      if (saved) {
        setAvailableStreams(JSON.parse(saved))
      } else {
        // Default streams if none in localStorage
        setAvailableStreams([
          {
            id: "edge01",
            label: "Operating Room Camera 1",
            url: "http://192.168.7.166:8889/live/cam/whep",
            description: "Primary surgical monitoring camera",
            type: "main",
            protocol: "webrtc",
            transport: "whep"
          },
          {
            id: "edge02", 
            label: "Operating Room Camera 2",
            url: "http://192.168.7.166:8890/live/cam/whep",
            description: "Secondary surgical monitoring camera",
            type: "main",
            protocol: "webrtc",
            transport: "whep"
          }
        ])
      }
    }
  }, [])

  const [activeSources, setActiveSources] = React.useState<StreamSource[]>(() => {
    return availableStreams.slice(0, 2) // Start with first 2 streams
  })
  
  const [activeTab, setActiveTab] = React.useState<string>(() => {
    return defaultActiveId || availableStreams[0]?.id || ""
  })

  // Update active sources when available streams change
  React.useEffect(() => {
    if (availableStreams.length > 0 && activeSources.length === 0) {
      const initialSources = availableStreams.slice(0, 2)
      setActiveSources(initialSources)
      if (initialSources.length > 0) {
        setActiveTab(initialSources[0].id)
      }
    }
  }, [availableStreams, activeSources.length])

  const addStreamSource = (source: StreamSource) => {
    if (activeSources.length >= maxTabs) return
    if (activeSources.find(s => s.id === source.id)) return
    
    setActiveSources(prev => [...prev, source])
    setActiveTab(source.id)
  }

  const removeStreamSource = (sourceId: string) => {
    setActiveSources(prev => {
      const newSources = prev.filter(s => s.id !== sourceId)
      if (activeTab === sourceId && newSources.length > 0) {
        setActiveTab(newSources[0].id)
      }
      return newSources
    })
  }

  const streamSourcesNotActive = availableStreams.filter(
    source => !activeSources.find(active => active.id === source.id)
  )

  const getSourceTypeIcon = (type?: string) => {
    switch (type) {
      case 'detection':
        return <Eye className="h-3 w-3" />
      case 'main':
        return <Video className="h-3 w-3" />
      default:
        return <Video className="h-3 w-3" />
    }
  }

  const getSourceTypeBadge = (type?: string) => {
    switch (type) {
      case 'detection':
        return <Badge variant="secondary" className="text-xs">AI</Badge>
      case 'main':
        return <Badge variant="outline" className="text-xs">Live</Badge>
      default:
        return <Badge variant="outline" className="text-xs">Custom</Badge>
    }
  }

  if (activeSources.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Multi-Stream Player</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center justify-center py-8">
          <Video className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-4">No streams available</p>
          <p className="text-sm text-muted-foreground">Add stream sources in the Stream Management section</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle>Multi-Stream Player</CardTitle>
          <div className="flex items-center space-x-2">
            {showAddButton && streamSourcesNotActive.length > 0 && activeSources.length < maxTabs && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    Add Stream
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Available Streams</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {streamSourcesNotActive.map((source) => (
                    <DropdownMenuItem
                      key={source.id}
                      onClick={() => addStreamSource(source)}
                    >
                      <div className="flex items-center justify-between w-full">
                        <div className="flex items-center space-x-2">
                          {getSourceTypeIcon(source.type)}
                          <span>{source.label}</span>
                        </div>
                        {getSourceTypeBadge(source.type)}
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="flex items-center justify-between mb-4">
            <TabsList className="grid" style={{ gridTemplateColumns: `repeat(${activeSources.length}, 1fr)` }}>
              {activeSources.map((source) => (
                <TabsTrigger key={source.id} value={source.id}>
                  <div className="flex items-center space-x-1">
                    {getSourceTypeIcon(source.type)}
                    <span className="truncate">{source.label}</span>
                  </div>
                </TabsTrigger>
              ))}
            </TabsList>
            
            {/* Remove buttons outside of TabsTrigger to avoid nesting */}
            {activeSources.length > 1 && (
              <div className="flex space-x-1">
                {activeSources.map((source) => (
                  <Button
                    key={`remove-${source.id}`}
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => removeStreamSource(source.id)}
                    title={`Remove ${source.label}`}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                ))}
              </div>
            )}
          </div>
          
          {activeSources.map((source) => (
            <TabsContent key={source.id} value={source.id} className="mt-4">
              <StreamPlayer
                streamUrl={source.url}
                title={source.label}
                className="w-full"
              />
              {source.description && (
                <p className="text-sm text-muted-foreground mt-2">
                  {source.description}
                </p>
              )}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </div>
  )
}