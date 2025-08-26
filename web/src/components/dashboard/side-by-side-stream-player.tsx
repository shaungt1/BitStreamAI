"use client"

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StreamPlayer } from "@/components/dashboard/stream-player"
import { StreamSource } from "@/types/stream"
import { defaultStreamSources } from "@/config/streams"
import { Video, Eye, Grid3X3, Grid2X2, Maximize2, Minimize2, X } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface SideBySideStreamPlayerProps {
  className?: string
  sources?: StreamSource[]
  defaultStreams?: string[]
  maxStreams?: number
}

type GridLayout = '1x1' | '1x2' | '2x2' | '2x3'

export function SideBySideStreamPlayer({
  className,
  sources = defaultStreamSources,
  defaultStreams = [],
  maxStreams = 6
}: SideBySideStreamPlayerProps) {
  const [activeStreams, setActiveStreams] = React.useState<StreamSource[]>(() => {
    const defaultSources = defaultStreams
      .map(id => sources.find(s => s.id === id))
      .filter(Boolean) as StreamSource[]
    
    if (defaultSources.length === 0) {
      // Default to first two main cameras
      return sources.filter(s => s.type === 'main').slice(0, 2)
    }
    
    return defaultSources
  })

  const [layout, setLayout] = React.useState<GridLayout>(() => {
    const count = activeStreams.length
    if (count <= 1) return '1x1'
    if (count <= 2) return '1x2'
    if (count <= 4) return '2x2'
    return '2x3'
  })

  const [fullscreenStream, setFullscreenStream] = React.useState<string | null>(null)

  const addStream = (source: StreamSource) => {
    if (activeStreams.length >= maxStreams) return
    if (activeStreams.find(s => s.id === source.id)) return
    
    const newStreams = [...activeStreams, source]
    setActiveStreams(newStreams)
    
    // Auto-adjust layout
    const count = newStreams.length
    if (count <= 1) setLayout('1x1')
    else if (count <= 2) setLayout('1x2')
    else if (count <= 4) setLayout('2x2')
    else setLayout('2x3')
  }

  const removeStream = (sourceId: string) => {
    const newStreams = activeStreams.filter(s => s.id !== sourceId)
    setActiveStreams(newStreams)
    
    if (fullscreenStream === sourceId) {
      setFullscreenStream(null)
    }
    
    // Auto-adjust layout
    const count = newStreams.length
    if (count <= 1) setLayout('1x1')
    else if (count <= 2) setLayout('1x2')
    else if (count <= 4) setLayout('2x2')
    else setLayout('2x3')
  }

  const availableSources = sources.filter(
    source => !activeStreams.find(active => active.id === source.id)
  )

  const getGridClass = (layout: GridLayout, streamCount: number) => {
    if (fullscreenStream) return "grid grid-cols-1"
    
    switch (layout) {
      case '1x1':
        return "grid grid-cols-1"
      case '1x2':
        return "grid grid-cols-1 md:grid-cols-2"
      case '2x2':
        return "grid grid-cols-1 md:grid-cols-2"
      case '2x3':
        return "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
      default:
        return "grid grid-cols-1 md:grid-cols-2"
    }
  }

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

  const getLayoutIcon = (layoutType: GridLayout) => {
    switch (layoutType) {
      case '1x1':
        return <Maximize2 className="h-4 w-4" />
      case '1x2':
        return <Grid2X2 className="h-4 w-4" />
      case '2x2':
        return <Grid2X2 className="h-4 w-4" />
      case '2x3':
        return <Grid3X3 className="h-4 w-4" />
      default:
        return <Grid2X2 className="h-4 w-4" />
    }
  }

  const visibleStreams = fullscreenStream 
    ? activeStreams.filter(s => s.id === fullscreenStream)
    : activeStreams

  return (
    <div className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CardTitle>Side-by-Side Viewer</CardTitle>
            {activeStreams.length > 0 && (
              <Badge variant="outline" className="text-xs">
                {activeStreams.length} stream{activeStreams.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {/* Layout Selector */}
            {activeStreams.length > 1 && !fullscreenStream && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    {getLayoutIcon(layout)}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Layout</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={() => setLayout('1x2')}
                    disabled={activeStreams.length < 2}
                  >
                    <Grid2X2 className="h-4 w-4 mr-2" />
                    1x2 Grid
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    onClick={() => setLayout('2x2')}
                    disabled={activeStreams.length < 3}
                  >
                    <Grid2X2 className="h-4 w-4 mr-2" />
                    2x2 Grid
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    onClick={() => setLayout('2x3')}
                    disabled={activeStreams.length < 5}
                  >
                    <Grid3X3 className="h-4 w-4 mr-2" />
                    2x3 Grid
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {/* Add Stream */}
            {availableSources.length > 0 && activeStreams.length < maxStreams && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Video className="h-4 w-4 mr-2" />
                    Add Stream
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Available Streams</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {availableSources.map((source) => (
                    <DropdownMenuItem
                      key={source.id}
                      onClick={() => addStream(source)}
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
        
        {fullscreenStream && (
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Maximize2 className="h-3 w-3" />
            <span>Fullscreen mode</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFullscreenStream(null)}
              className="h-6 px-2"
            >
              <Minimize2 className="h-3 w-3 mr-1" />
              Exit
            </Button>
          </div>
        )}
      </CardHeader>
      
      <CardContent>
        {activeStreams.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Video className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No streams selected</h3>
            <p className="text-muted-foreground mb-4 text-center">
              Add camera feeds to view them side-by-side for comparison
            </p>
            {availableSources.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button>
                    <Video className="h-4 w-4 mr-2" />
                    Add First Stream
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuLabel>Available Streams</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {availableSources.map((source) => (
                    <DropdownMenuItem
                      key={source.id}
                      onClick={() => addStream(source)}
                    >
                      <div className="flex items-center space-x-2">
                        {getSourceTypeIcon(source.type)}
                        <span>{source.label}</span>
                        {getSourceTypeBadge(source.type)}
                      </div>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        ) : (
          <div className={`${getGridClass(layout, activeStreams.length)} gap-4`}>
            {visibleStreams.map((source) => (
              <div key={source.id} className="relative group">
                <div className="absolute top-2 right-2 z-10 flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {!fullscreenStream && (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => setFullscreenStream(source.id)}
                    >
                      <Maximize2 className="h-3 w-3" />
                    </Button>
                  )}
                  {activeStreams.length > 1 && (
                    <Button
                      variant="destructive"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={() => removeStream(source.id)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
                <StreamPlayer
                  streamUrl={source.url}
                  title={source.label}
                  className="w-full"
                />
                {source.description && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {source.description}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </div>
  )
}