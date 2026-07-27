"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Monitor, Wifi, WifiOff, AlertCircle, CheckCircle2, XCircle, Loader2, Maximize2, Minimize2, RefreshCw, List, Terminal, Play } from "lucide-react";

interface StepData {
  event: "stepBegin" | "stepEnd";
  id: string;
  title?: string;
  category?: string;
  startTime?: number;
  error?: string;
}

interface Frame {
  type: "screenshot" | "log" | "status" | "error" | "done" | "ping" | "step";
  data?: any;          // base64 image or StepData object
  mime?: string;
  text?: string;       // log frames
  value?: string;      // status frames: "connecting" | "running" | "passed" | "failed"
  url?: string;
  message?: string;    // error frames
  result?: unknown;
  frame?: number;
}

export interface TestStep {
  id: string;
  title: string;
  category: string;
  status: "running" | "passed" | "failed";
  error?: string;
  startTime: number;
}

type StreamStatus = "idle" | "connecting" | "running" | "passed" | "failed" | "error" | "done";

interface BrowserLiveViewProps {
  jobId: string;
  /** WebSocket URL, e.g. ws://localhost:8000 */
  wsBaseUrl?: string;
  /** Called when stream ends */
  onDone?: () => void;
}

const STATUS_CONFIG: Record<StreamStatus, { label: string; color: string; icon: React.FC<{ className?: string }> }> = {
  idle:       { label: "Waiting...",  color: "text-zinc-400",   icon: Loader2 },
  connecting: { label: "Connecting", color: "text-blue-400",   icon: Loader2 },
  running:    { label: "Running",    color: "text-purple-400", icon: Monitor },
  passed:     { label: "Passed",     color: "text-emerald-400",icon: CheckCircle2 },
  failed:     { label: "Failed",     color: "text-red-400",    icon: XCircle },
  error:      { label: "Error",      color: "text-orange-400", icon: AlertCircle },
  done:       { label: "Done",       color: "text-zinc-400",   icon: CheckCircle2 },
};

export default function BrowserLiveView({ jobId, wsBaseUrl, onDone }: BrowserLiveViewProps) {
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<StreamStatus>("idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [steps, setSteps] = useState<TestStep[]>([]);
  const [activeTab, setActiveTab] = useState<"steps" | "console">("steps");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [targetUrl, setTargetUrl] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [fps, setFps] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);
  const fpsCounterRef = useRef(0);
  const fpsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const getWsUrl = useCallback(() => {
    if (wsBaseUrl) return `${wsBaseUrl}/ws/browser/${jobId}`;

    if (process.env.NEXT_PUBLIC_WS_URL) {
      return `${process.env.NEXT_PUBLIC_WS_URL}/ws/browser/${jobId}`;
    }

    if (process.env.NEXT_PUBLIC_API_URL) {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const wsProto = apiUrl.startsWith("https") ? "wss:" : "ws:";
      const host = apiUrl.replace(/^https?:\/\//, "");
      return `${wsProto}//${host}/ws/browser/${jobId}`;
    }

    const base = typeof window !== "undefined"
      ? `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.hostname}:8000`
      : "ws://localhost:8000";
    return `${base}/ws/browser/${jobId}`;
  }, [wsBaseUrl, jobId]);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return; // already open/connecting

    const wsUrl = getWsUrl();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      setStreamStatus("connecting");
      setSteps([]);
      setLogs([]);
      setCurrentFrame(null);
      setErrorMsg(null);
    };

    ws.onclose = () => {
      setWsConnected(false);
    };

    ws.onerror = () => {
      setWsConnected(false);
    };

    ws.onmessage = (event) => {
      let frame: Frame;
      try {
        frame = JSON.parse(event.data as string);
      } catch {
        return;
      }

      switch (frame.type) {
        case "screenshot":
          if (frame.data) {
            const mime = frame.mime || "image/jpeg";
            setCurrentFrame(`data:${mime};base64,${frame.data}`);
            fpsCounterRef.current += 1;
          }
          break;

        case "step":
          if (frame.data) {
            const stepData = frame.data as StepData;
            if (stepData.event === "stepBegin" && stepData.title && stepData.category) {
              setSteps((prev) => [...prev, {
                id: stepData.id,
                title: stepData.title!,
                category: stepData.category!,
                status: "running",
                startTime: stepData.startTime || Date.now()
              }]);
            } else if (stepData.event === "stepEnd") {
              setSteps((prev) => prev.map(s => s.id === stepData.id ? {
                ...s,
                status: stepData.error ? "failed" : "passed",
                error: stepData.error
              } : s));
            }
          }
          break;

        case "log":
          if (frame.text) {
            setLogs((prev) => [...prev.slice(-199), frame.text!]);
          }
          break;

        case "status":
          if (frame.value) {
            setStreamStatus(frame.value as StreamStatus);
          }
          if (frame.url) {
            setTargetUrl(frame.url);
          }
          break;

        case "error":
          setStreamStatus("error");
          setErrorMsg(frame.message || "Unknown error");
          break;

        case "done":
          setStreamStatus("done");
          ws.close();
          onDone?.();
          break;

        case "ping":
          // keepalive, no action needed
          break;
      }
    };
  }, [getWsUrl, onDone]);

  // Auto-connect when component mounts
  useEffect(() => {
    // Small delay so the backend has time to create the job queue
    reconnectTimerRef.current = setTimeout(connect, 800);

    // FPS meter
    fpsTimerRef.current = setInterval(() => {
      setFps(fpsCounterRef.current);
      fpsCounterRef.current = 0;
    }, 1000);

    return () => {
      wsRef.current?.close();
      if (fpsTimerRef.current) clearInterval(fpsTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, [connect]);

  // Auto-scroll logs
  useEffect(() => {
    if (activeTab === "console") {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, activeTab]);

  // Auto-scroll steps
  const stepsEndRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (activeTab === "steps") {
      stepsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [steps, activeTab]);

  const statusCfg = STATUS_CONFIG[streamStatus] ?? STATUS_CONFIG.idle;
  const StatusIcon = statusCfg.icon;
  const isLoading = streamStatus === "idle" || streamStatus === "connecting";

  return (
    <div
      className={`
        flex flex-col bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl
        transition-all duration-300
        ${isExpanded ? "fixed inset-4 z-[60]" : "w-full"}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-zinc-900/80 border-b border-zinc-800 flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          {/* Live indicator */}
          <div className="relative flex items-center gap-2">
            <span
              className={`
                flex h-2.5 w-2.5 rounded-full
                ${wsConnected ? "bg-emerald-500" : "bg-zinc-600"}
              `}
            >
              {wsConnected && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
            </span>
            <span className="text-xs font-semibold text-zinc-300 tracking-widest uppercase">
              Live
            </span>
          </div>

          <div className="w-px h-4 bg-zinc-700" />

          {/* Status badge */}
          <div className={`flex items-center gap-1.5 text-xs font-medium ${statusCfg.color}`}>
            <StatusIcon
              className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`}
            />
            <span>{statusCfg.label}</span>
          </div>

          {/* Target URL */}
          {targetUrl && (
            <>
              <div className="w-px h-4 bg-zinc-700" />
              <span className="text-xs text-zinc-500 truncate max-w-[240px]" title={targetUrl}>
                {targetUrl}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {/* FPS counter */}
          {streamStatus === "running" && (
            <span className="text-xs text-zinc-600 font-mono tabular-nums">
              {fps} fps
            </span>
          )}

          {/* Connection indicator */}
          <span title={wsConnected ? "WebSocket connected" : "WebSocket disconnected"}>
            {wsConnected
              ? <Wifi className="h-4 w-4 text-emerald-500" />
              : <WifiOff className="h-4 w-4 text-zinc-600" />}
          </span>

          {/* Reconnect button */}
          {!wsConnected && (
            <button
              onClick={connect}
              className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
              title="Reconnect"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          )}

          {/* Expand/collapse */}
          <button
            onClick={() => setIsExpanded((v) => !v)}
            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
            title={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Main content: screenshot + log panel */}
      <div className={`flex ${isExpanded ? "flex-row flex-1 min-h-0" : "flex-col"} overflow-hidden`}>

        {/* Screenshot viewport */}
        <div
          className={`
            relative bg-zinc-900 flex items-center justify-center overflow-hidden
            ${isExpanded ? "flex-1 min-w-0" : "w-full aspect-video"}
          `}
          style={{ minHeight: isExpanded ? undefined : "240px" }}
        >
          {/* Browser chrome bar */}
          <div className="absolute top-0 left-0 right-0 z-10 bg-zinc-800/90 backdrop-blur-sm px-3 py-1.5 flex items-center gap-2 border-b border-zinc-700/50">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
            </div>
            <div className="flex-1 bg-zinc-700/50 rounded text-xs text-zinc-400 px-2 py-0.5 font-mono truncate">
              {targetUrl || "about:blank"}
            </div>
          </div>

          {/* Frame display */}
          {currentFrame ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={currentFrame}
              alt="Live browser view"
              className="w-full h-full object-contain object-top mt-7"
              style={{ imageRendering: "auto" }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center gap-3 text-zinc-600 mt-7">
              {isLoading ? (
                <>
                  <Loader2 className="h-8 w-8 animate-spin text-zinc-700" />
                  <span className="text-sm">Waiting for browser frames…</span>
                </>
              ) : errorMsg ? (
                <>
                  <AlertCircle className="h-8 w-8 text-orange-500/70" />
                  <span className="text-sm text-orange-400/80 text-center max-w-xs">{errorMsg}</span>
                </>
              ) : (
                <>
                  <Monitor className="h-8 w-8" />
                  <span className="text-sm">No frames received yet</span>
                </>
              )}
            </div>
          )}

          {/* Scanline overlay for the "live feed" effect */}
          <div
            className="pointer-events-none absolute inset-0 mt-7"
            style={{
              background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px)",
            }}
          />
        </div>

        {/* Side Panel: Steps / Logs */}
        <div
          className={`
            flex flex-col bg-zinc-950 border-zinc-800
            ${isExpanded ? "w-80 border-l flex-shrink-0" : "border-t"}
            overflow-hidden transition-all duration-300
          `}
          style={{ maxHeight: isExpanded ? undefined : "300px", minHeight: isExpanded ? undefined : "200px" }}
        >
          {/* Tabs */}
          <div className="flex border-b border-zinc-800 flex-shrink-0">
            <button
              onClick={() => setActiveTab("steps")}
              className={`flex-1 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === "steps" ? "bg-zinc-800/50 text-emerald-400 border-b-2 border-emerald-500" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"}`}
            >
              <List className="w-3.5 h-3.5" />
              Steps ({steps.length})
            </button>
            <button
              onClick={() => setActiveTab("console")}
              className={`flex-1 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === "console" ? "bg-zinc-800/50 text-blue-400 border-b-2 border-blue-500" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"}`}
            >
              <Terminal className="w-3.5 h-3.5" />
              Console
            </button>
          </div>

          <div className="flex-1 overflow-y-auto relative">
            {/* Steps Tab */}
            {activeTab === "steps" && (
              <div className="p-2 space-y-1">
                {steps.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-zinc-600 mt-10 space-y-2">
                    <Play className="w-6 h-6 opacity-50" />
                    <span className="text-xs">Waiting for test steps...</span>
                  </div>
                ) : (
                  steps.map((step, i) => (
                    <div 
                      key={step.id} 
                      className={`
                        flex flex-col p-2.5 rounded-lg border text-sm transition-all
                        ${step.status === "running" ? "bg-blue-500/10 border-blue-500/30 shadow-[0_0_10px_rgba(59,130,246,0.1)]" : ""}
                        ${step.status === "passed" ? "bg-emerald-500/5 border-emerald-500/20 opacity-80" : ""}
                        ${step.status === "failed" ? "bg-red-500/10 border-red-500/30" : ""}
                      `}
                    >
                      <div className="flex items-start gap-2.5">
                        <div className="mt-0.5 flex-shrink-0">
                          {step.status === "running" && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                          {step.status === "passed" && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                          {step.status === "failed" && <XCircle className="w-4 h-4 text-red-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`font-medium truncate ${step.status === "running" ? "text-blue-100" : "text-zinc-200"}`}>
                            {step.title}
                          </div>
                          <div className="text-[10px] text-zinc-500 font-mono mt-0.5 tracking-wider uppercase">
                            {step.category}
                          </div>
                          {step.error && (
                            <div className="mt-1.5 text-xs text-red-400 bg-red-950/50 p-1.5 rounded border border-red-900/50 break-words font-mono">
                              {step.error}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
                <div ref={stepsEndRef} />
              </div>
            )}

            {/* Console Tab */}
            {activeTab === "console" && (
              <div className="p-2 font-mono space-y-0.5">
                {errorMsg && (
                  <div className="text-xs text-orange-400 px-1 mb-2 bg-orange-950/30 p-2 rounded border border-orange-900/50">
                    [System Error] {errorMsg}
                  </div>
                )}
                {logs.length === 0 && !errorMsg ? (
                  <div className="flex items-center justify-center h-full text-zinc-600 mt-10">
                    <span className="text-xs">No logs yet...</span>
                  </div>
                ) : (
                  logs.map((line, i) => (
                    <div key={i} className="text-xs text-zinc-400 hover:text-zinc-300 leading-relaxed px-1 break-all transition-colors hover:bg-zinc-900/50 rounded">
                      {line}
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
