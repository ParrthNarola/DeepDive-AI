"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, Zap } from "lucide-react";
import type { WSEvent } from "@/hooks/useWebSocket";

type LogEntry = {
  id: number;
  timestamp: string;
  message: string;
  event?: string;
};

type EmbedProgress = {
  current: number;
  total: number;
  percentage: number;
} | null;

type Props = {
  subscribe: (cb: (e: WSEvent) => void) => () => void;
};

let nextId = 0;

export default function ActivityFeed({ subscribe }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [embedProgress, setEmbedProgress] = useState<EmbedProgress>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type !== "pipeline_event") return;

      // Track embedding progress separately for the progress bar
      if (event.event === "embedding_progress") {
        setEmbedProgress({
          current: event.current as number,
          total: event.total as number,
          percentage: event.percentage as number,
        });
        // Also log it as a line
        setLogs((prev) => [
          ...prev.slice(-200),
          {
            id: nextId++,
            timestamp: new Date().toLocaleTimeString(),
            message: event.message as string,
            event: event.event as string,
          },
        ]);
        return;
      }

      // Clear progress bar when embedding finishes
      if (
        event.event === "processing_complete" ||
        event.event === "processing_error"
      ) {
        setEmbedProgress(null);
      }

      setLogs((prev) => [
        ...prev.slice(-200),
        {
          id: nextId++,
          timestamp: new Date().toLocaleTimeString(),
          message: event.message as string,
          event: event.event as string,
        },
      ]);
    });
    return unsub;
  }, [subscribe]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, embedProgress]);

  const getEventColor = (event?: string) => {
    if (!event) return "text-white/60";
    if (event.includes("error")) return "text-red-400";
    if (event === "processing_complete" || event.includes("end"))
      return "text-emerald-400";
    if (event.includes("start") || event.includes("received"))
      return "text-cyan-400";
    if (event.includes("progress") || event.includes("embedding"))
      return "text-amber-400";
    if (event.includes("complete")) return "text-emerald-400";
    return "text-white/60";
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-black/40 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <Terminal className="h-4 w-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-white/80">Pipeline Activity</h3>
        <span className="ml-auto rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
          LIVE
        </span>
      </div>

      {/* Embedding progress bar — shown only while embedding is active */}
      {embedProgress && (
        <div className="border-b border-white/10 px-4 py-3">
          <div className="mb-1.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Zap className="h-3.5 w-3.5 animate-pulse text-amber-400" />
              <span className="text-[11px] font-medium text-amber-400">
                Embedding chunks
              </span>
            </div>
            <span className="font-mono text-[11px] text-white/50">
              {embedProgress.current}/{embedProgress.total} &nbsp;
              <span className="text-amber-400 font-semibold">
                {embedProgress.percentage}%
              </span>
            </span>
          </div>
          {/* Track */}
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            {/* Fill */}
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-500 to-amber-300 transition-all duration-300 ease-out"
              style={{ width: `${embedProgress.percentage}%` }}
            />
          </div>
        </div>
      )}

      {/* Log area */}
      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs leading-relaxed">
        {logs.length === 0 && (
          <p className="py-8 text-center text-white/30">
            Upload a document to see pipeline activity…
          </p>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex gap-2 py-0.5">
            <span className="shrink-0 text-white/30">{log.timestamp}</span>
            <span className={getEventColor(log.event)}>{log.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
