"use client"

import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { StreamPlayer } from "@/components/dashboard/stream-player"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Video,
  Eye,
  Brain,
  Activity,
  Plus,
  Settings,
  Play,
  AlertTriangle,
  CheckCircle,
  Clock,
  Cpu,
  MoreHorizontal,
} from "lucide-react"

interface StreamHealthCardProps {
  className?: string
}

function StreamHealthCard({ className }: StreamHealthCardProps) {
  const streams = [
    { id: "camera01", name: "Main Entrance", status: "up", fps: 30 },
    { id: "camera02", name: "Loading Dock", status: "up", fps: 28 },
    { id: "camera03", name: "Parking Lot", status: "degraded", fps: 15 },
    { id: "camera04", name: "Server Room", status: "down", fps: 0 },
  ]

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Stream Health</CardTitle>
        <Video className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {streams.map((stream) => (
            <div key={stream.id} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className={`h-2 w-2 rounded-full ${
                  stream.status === 'up' ? 'bg-green-500' :
                  stream.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'
                }`} />
                <span className="text-sm font-medium">{stream.name}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-muted-foreground">{stream.fps} FPS</span>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                      <MoreHorizontal className="h-3 w-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem>Open Viewer</DropdownMenuItem>
                    <DropdownMenuItem>Restart Stream</DropdownMenuItem>
                    <DropdownMenuItem>Configure</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function YoloPipelineCard({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">YOLO-112 Pipeline</CardTitle>
        <Eye className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-2xl font-bold">847</div>
            <p className="text-xs text-muted-foreground">Objects/min</p>
          </div>
          <div>
            <div className="text-2xl font-bold">28.5</div>
            <p className="text-xs text-muted-foreground">Avg FPS</p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>GPU Utilization</span>
            <span>67%</span>
          </div>
          <Progress value={67} className="h-2" />
        </div>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span>Queue Depth</span>
            <span>12 frames</span>
          </div>
          <Progress value={24} className="h-2" />
        </div>
        <div className="text-xs text-muted-foreground">
          Last detection: 2 seconds ago
        </div>
      </CardContent>
    </Card>
  )
}

function LLMFeedsCard({ className }: { className?: string }) {
  const models = [
    { name: "GPT-4 Vision", status: "active", latency: 1200, tokens: 45 },
    { name: "Claude-3 Opus", status: "active", latency: 890, tokens: 32 },
    { name: "Gemini Pro", status: "overloaded", latency: 3400, tokens: 18 },
  ]

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">LLM Feeds</CardTitle>
        <Brain className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <Accordion type="single" collapsible>
          <AccordionItem value="models" className="border-none">
            <AccordionTrigger className="py-2 text-sm">
              Active Models ({models.length})
            </AccordionTrigger>
            <AccordionContent className="space-y-3">
              {models.map((model) => (
                <div key={model.name} className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <Badge 
                        variant={model.status === 'active' ? 'default' : 'destructive'}
                        className="text-xs"
                      >
                        {model.status}
                      </Badge>
                      <span className="text-sm font-medium">{model.name}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {model.latency}ms • {model.tokens} tok/s
                    </div>
                  </div>
                </div>
              ))}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  )
}

function RecentAlertsCard({ className }: { className?: string }) {
  const alerts = [
    { id: 1, time: "2 min ago", type: "detection", message: "Person detected in restricted area", severity: "high" },
    { id: 2, time: "5 min ago", type: "system", message: "Camera03 FPS dropped below threshold", severity: "medium" },
    { id: 3, time: "12 min ago", type: "detection", message: "Vehicle parked in loading zone", severity: "low" },
  ]

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Recent Alerts</CardTitle>
        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">Time</TableHead>
              <TableHead className="text-xs">Alert</TableHead>
              <TableHead className="text-xs">Severity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {alerts.map((alert) => (
              <TableRow key={alert.id} className="cursor-pointer hover:bg-muted/50">
                <TableCell className="text-xs text-muted-foreground">
                  {alert.time}
                </TableCell>
                <TableCell className="text-xs">
                  {alert.message}
                </TableCell>
                <TableCell>
                  <Badge 
                    variant={
                      alert.severity === 'high' ? 'destructive' :
                      alert.severity === 'medium' ? 'default' : 'secondary'
                    }
                    className="text-xs"
                  >
                    {alert.severity}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function QuickActionsCard({ className }: { className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-medium">Quick Actions</CardTitle>
        <Activity className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Button className="w-full justify-start" variant="outline">
          <Plus className="mr-2 h-4 w-4" />
          Add Stream
        </Button>
        <Button className="w-full justify-start" variant="outline">
          <Eye className="mr-2 h-4 w-4" />
          Enable YOLO-112
        </Button>
        <Button className="w-full justify-start" variant="outline">
          <Brain className="mr-2 h-4 w-4" />
          Attach LLM Feed
        </Button>
        <Button className="w-full justify-start" variant="outline">
          <Settings className="mr-2 h-4 w-4" />
          Open Live Logs
        </Button>
      </CardContent>
    </Card>
  )
}

export function HomePage() {
  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your edge device streams, detections, and AI models in real-time
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            <CheckCircle className="mr-1 h-3 w-3" />
            All Systems Operational
          </Badge>
        </div>
      </div>

      {/* Live Stream Section */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <StreamPlayer 
            title="Main CSI Camera Feed"
            className="h-full"
          />
        </div>
        <div className="space-y-6">
          <StreamHealthCard />
          <QuickActionsCard />
        </div>
      </div>

      {/* Monitoring Cards Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <YoloPipelineCard />
        <LLMFeedsCard />
        <RecentAlertsCard />
      </div>

      {/* System Overview */}
      <Card>
        <CardHeader>
          <CardTitle>System Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-4">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Video className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium">Active Streams</span>
              </div>
              <div className="text-2xl font-bold">3/4</div>
              <div className="text-xs text-muted-foreground">Cameras online</div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Eye className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium">YOLO Detections</span>
              </div>
              <div className="text-2xl font-bold">1,247</div>
              <div className="text-xs text-muted-foreground">Today</div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Brain className="h-4 w-4 text-purple-600" />
                <span className="text-sm font-medium">LLM Queries</span>
              </div>
              <div className="text-2xl font-bold">89</div>
              <div className="text-xs text-muted-foreground">Last hour</div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Cpu className="h-4 w-4 text-orange-600" />
                <span className="text-sm font-medium">Edge Devices</span>
              </div>
              <div className="text-2xl font-bold">2</div>
              <div className="text-xs text-muted-foreground">Connected</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}