"use client";

import { useState, useCallback } from "react";
import { Layers, Wifi, WifiOff } from "lucide-react";
import { useWebSocket } from "@/hooks/useWebSocket";
import UploadPanel from "@/components/UploadPanel";
import ActivityFeed from "@/components/ActivityFeed";
import ResourceMonitor from "@/components/ResourceMonitor";
import ChatPanel from "@/components/ChatPanel";
import DocumentList from "@/components/DocumentList";

export default function DashboardPage() {
  const { connected, subscribe } = useWebSocket();
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  const handleUploaded = useCallback((docId: string, _filename: string) => {
    setSelectedDocId(docId);
  }, []);

  return (
    <div className="flex h-screen">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside className="flex w-72 shrink-0 flex-col border-r border-white/10 bg-black/30 backdrop-blur-lg">
        {/* Logo / brand */}
        <div className="flex items-center gap-3 border-b border-white/10 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
            <Layers className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight glow-text">DeepDive AI</h1>
            <p className="text-[10px] uppercase tracking-widest text-white/30">Research Assistant</p>
          </div>
        </div>

        {/* Connection indicator */}
        <div className="flex items-center gap-2 border-b border-white/10 px-5 py-2.5">
          {connected ? (
            <>
              <Wifi className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-xs text-emerald-400/80">Connected</span>
              <span className="ml-auto h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5 text-red-400" />
              <span className="text-xs text-red-400/80">Disconnected</span>
            </>
          )}
        </div>

        {/* Upload zone */}
        <div className="border-b border-white/10 px-4 py-4">
          <UploadPanel onUploaded={handleUploaded} />
        </div>

        {/* Document list */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <DocumentList selectedId={selectedDocId} onSelect={setSelectedDocId} subscribe={subscribe} />
        </div>

        {/* Footer */}
        <div className="border-t border-white/10 px-5 py-3">
          <p className="text-[10px] text-white/20">DeepDive AI v1.0 — Powered by Gemini</p>
        </div>
      </aside>

      {/* ── Main Content ────────────────────────────────────── */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center border-b border-white/10 px-6 py-3">
          <h2 className="text-sm font-semibold text-white/70">Dashboard</h2>
          <div className="ml-auto flex items-center gap-2">
            <span className="rounded-full bg-white/[0.06] px-3 py-1 text-[11px] font-medium text-white/40">
              Qwen2.5-72B · all-MiniLM-L6-v2
            </span>
          </div>
        </header>

        {/* Dashboard grid */}
        <div className="flex-1 overflow-auto p-5">
          <div className="grid h-full grid-cols-2 grid-rows-[auto_1fr] gap-4">
            {/* Resource monitor — top-left */}
            <div>
              <ResourceMonitor subscribe={subscribe} />
            </div>

            {/* Placeholder/Stats — top-right */}
            <div className="rounded-2xl border border-white/10 bg-black/40 p-4 backdrop-blur-sm flex items-center justify-center">
              <div className="text-center">
                <p className="text-3xl font-bold glow-text">DeepDive</p>
                <p className="mt-1 text-xs text-white/40">Upload a PDF → Process → Chat with AI</p>
              </div>
            </div>

            {/* Activity feed — bottom-left */}
            <div className="min-h-0">
              <ActivityFeed subscribe={subscribe} />
            </div>

            {/* Chat — bottom-right */}
            <div className="min-h-0">
              <ChatPanel documentId={selectedDocId} subscribe={subscribe} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
