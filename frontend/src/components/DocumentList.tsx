"use client";

import { useEffect, useState } from "react";
import { FileText, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import { getDocuments } from "@/lib/api";
import type { WSEvent } from "@/hooks/useWebSocket";

type Doc = { id: string; filename: string; status: string };

type Props = {
  selectedId: string | null;
  onSelect: (id: string) => void;
  subscribe: (cb: (e: WSEvent) => void) => () => void;
};

export default function DocumentList({ selectedId, onSelect, subscribe }: Props) {
  const [docs, setDocs] = useState<Doc[]>([]);

  // Refresh list on pipeline events
  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type !== "pipeline_event") return;

      if (event.event === "file_received") {
        // New document incoming — fetch fresh list
        fetchDocs();
      } else if (event.event === "processing_complete" && event.doc_id) {
        // Mark the specific doc as ready immediately without a full refetch
        setDocs((prev) =>
          prev.map((d) =>
            d.id === event.doc_id ? { ...d, status: "ready" } : d
          )
        );
      } else if (event.event === "processing_error" && event.doc_id) {
        setDocs((prev) =>
          prev.map((d) =>
            d.id === event.doc_id ? { ...d, status: "error" } : d
          )
        );
      }
    });
    return unsub;
  }, [subscribe]);

  const fetchDocs = async () => {
    try {
      const data = await getDocuments();
      setDocs(data.documents);
    } catch {}
  };

  // Initial fetch
  useEffect(() => {
    fetchDocs();
  }, []);

  const statusIcon = (status: string) => {
    switch (status) {
      case "ready":
        return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
      case "processing":
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />;
      default:
        return <AlertCircle className="h-3.5 w-3.5 text-red-400" />;
    }
  };

  return (
    <div className="space-y-1.5">
      <h3 className="mb-3 px-1 text-xs font-semibold uppercase tracking-wider text-white/40">Documents</h3>
      {docs.length === 0 && <p className="px-1 text-xs text-white/25">No documents yet</p>}
      {docs.map((doc) => (
        <button
          key={doc.id}
          onClick={() => doc.status === "ready" && onSelect(doc.id)}
          className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition-all ${
            selectedId === doc.id
              ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-white border border-cyan-500/30"
              : "text-white/60 hover:bg-white/[0.06] hover:text-white/80 border border-transparent"
          } ${doc.status !== "ready" ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
        >
          <FileText className="h-4 w-4 shrink-0 text-white/40" />
          <span className="flex-1 truncate">{doc.filename}</span>
          {statusIcon(doc.status)}
        </button>
      ))}
    </div>
  );
}
