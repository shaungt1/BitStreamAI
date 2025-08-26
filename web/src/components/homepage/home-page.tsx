"use client"

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { StreamPlayer } from "@/components/dashboard/stream-player"
import { MultiStreamPlayer } from "@/components/dashboard/multi-stream-player"
import { SideBySideStreamPlayer } from "@/components/dashboard/side-by-side-stream-player"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StreamSource } from "@/types/stream"
import { loadStreamsFromStorage, saveStreamsToStorage, addStreamSource } from "@/config/streams"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Video,
  Eye,
  Brain,
  Activity,
  Plus,
  Settings,
  CheckCircle,
  Trash2,
  Monitor,
  Grid3X3,
  Grid2X2,
} from "lucide-react"

export function HomePage() {
  // Stream management state
  const [streams, setStreams] = React.useState<StreamSource[]>([])
  const [isAddDialogOpen, setIsAddDialogOpen] = React.useState(false)
  const [newStream, setNewStream] = React.useState({
    label: "",
    url: "",
    description: "",
    type: "main" as const,
    protocol: "webrtc" as const,
    transport: "whep" as const,
    aiSources: [] as string[]
  })

  // View state
  const [activeView, setActiveView] = React.useState("single")
  const [gridLayout, setGridLayout] = React.useState("2x2")

  // Analytics state
  const [connectedStreams, setConnectedStreams] = React.useState(0)
  const [yoloDetections, setYoloDetections] = React.useState(0)

  React.useEffect(() => {
    const loadedStreams = loadStreamsFromStorage()
    setStreams(loadedStreams)
  }, [])

  React.useEffect(() => {
    saveStreamsToStorage(streams)
  }, [streams])

  const handleAddStream = () => {
    if (!newStream.label || !newStream.url) return
    
    const stream = addStreamSource({
      label: newStream.label,
      url: newStream.url,
      description: newStream.description,
      type: newStream.type,
      protocol: newStream.protocol,
      transport: newStream.transport,
      aiSources: newStream.aiSources,
      aiSourcesCount: newStream.aiSources.length
    })
    
    setStreams(prev => [...prev, stream])
    setNewStream({ 
      label: "", 
      url: "", 
      description: "", 
      type: "main", 
      protocol: "webrtc", 
      transport: "whep",
      aiSources: []
    })
    setIsAddDialogOpen(false)
  }

  const removeStream = (id: string) => {
    setStreams(prev => prev.filter(s => s.id !== id))
  }

  return (
    <div className="flex-1 space-y-4 p-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">BitStream AI Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor and analyze video streams from edge devices for healthcare and security applications
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            <CheckCircle className="mr-1 h-3 w-3" />
            System Online
          </Badge>
        </div>
      </div>

      {/* View Controls Card - Separate from video */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <Monitor className="h-5 w-5" />
              <span>Stream View Controls</span>
            </CardTitle>
            <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-blue-600 hover:bg-blue-700">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Stream Source
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add New Stream Source</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="label">Stream Label</Label>
                    <Input
                      id="label"
                      placeholder="e.g., OR Camera 3"
                      value={newStream.label}
                      onChange={(e) => setNewStream(prev => ({ ...prev, label: e.target.value }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="url">Stream URL</Label>
                    <Input
                      id="url"
                      placeholder="http://192.168.x.x:8889/live/cam/whep"
                      value={newStream.url}
                      onChange={(e) => setNewStream(prev => ({ ...prev, url: e.target.value }))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      placeholder="Brief description"
                      value={newStream.description}
                      onChange={(e) => setNewStream(prev => ({ ...prev, description: e.target.value }))}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleAddStream} 
                      disabled={!newStream.label || !newStream.url}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      Add Stream
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-4">
            <Tabs value={activeView} onValueChange={setActiveView} className="flex-1">
              <TabsList className="grid w-full grid-cols-3 max-w-md">
                <TabsTrigger value="single">Single View</TabsTrigger>
                <TabsTrigger value="multi">Multi-Stream</TabsTrigger>
                <TabsTrigger value="sidebyside">Side-by-Side</TabsTrigger>
              </TabsList>
            </Tabs>
            
            {(activeView === "multi" || activeView === "sidebyside") && (
              <div className="flex items-center space-x-2">
                <Label className="text-sm">Grid:</Label>
                <Select value={gridLayout} onValueChange={setGridLayout}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1x2">
                      <div className="flex items-center space-x-2">
                        <Grid2X2 className="h-4 w-4" />
                        <span>1x2</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="2x2">
                      <div className="flex items-center space-x-2">
                        <Grid2X2 className="h-4 w-4" />
                        <span>2x2</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="2x3">
                      <div className="flex items-center space-x-2">
                        <Grid3X3 className="h-4 w-4" />
                        <span>2x3</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Layout */}
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Video Feed Area - Left Side (3/4 width) */}
        <div className="lg:col-span-3">
          <Tabs value={activeView} className="w-full">
            <TabsContent value="single" className="mt-0">
              <StreamPlayer 
                title="OR Camera 1"
                streamUrl="http://192.168.7.166:8889/live/cam/whep"
                className="w-full"
              />
            </TabsContent>
            
            <TabsContent value="multi" className="mt-0">
              <MultiStreamPlayer className="w-full" />
            </TabsContent>
            
            <TabsContent value="sidebyside" className="mt-0">
              <SideBySideStreamPlayer 
                className="w-full"
                defaultStreams={["edge01", "edge02"]}
              />
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Quick Actions - Above Stream Sources */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button className="w-full justify-start bg-blue-600 hover:bg-blue-700">
                <Eye className="mr-2 h-4 w-4" />
                Enable YOLO Detection
              </Button>
              <Button className="w-full justify-start bg-blue-600 hover:bg-blue-700">
                <Brain className="mr-2 h-4 w-4" />
                Configure LLM Analysis
              </Button>
              <Button className="w-full justify-start" variant="outline">
                <Settings className="mr-2 h-4 w-4" />
                System Settings
              </Button>
            </CardContent>
          </Card>

          {/* Stream Sources */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Stream Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {streams.map((stream) => (
                <div key={stream.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <div className="font-medium text-sm">{stream.label}</div>
                    <div className="text-xs text-muted-foreground truncate">
                      {stream.url}
                    </div>
                    <div className="flex items-center space-x-1 mt-1">
                      <Badge variant="outline" className="text-xs">
                        {stream.type === 'detection' ? 'AI Detection' : 'Live Feed'}
                      </Badge>
                      {stream.aiSourcesCount && stream.aiSourcesCount > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {stream.aiSourcesCount} AI
                        </Badge>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeStream(stream.id)}
                    className="h-8 w-8 p-0"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* System Analytics - Bottom */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Connected Streams</CardTitle>
            <Video className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{connectedStreams}</div>
            <p className="text-xs text-muted-foreground">
              Active edge devices
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">YOLO Detections</CardTitle>
            <Eye className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{yoloDetections}</div>
            <p className="text-xs text-muted-foreground">
              Objects detected today
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">LLM Processing</CardTitle>
            <Brain className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Ready</div>
            <p className="text-xs text-muted-foreground">
              AI analysis available
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Activity className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">Online</div>
            <p className="text-xs text-muted-foreground">
              All systems operational
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}