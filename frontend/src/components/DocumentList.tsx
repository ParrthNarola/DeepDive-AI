"use client";

import { useEffect, useState } from "react";
import { FileText, CheckCircle2, Loader2, AlertCircle, Trash2 } from "lucide-react";
import { getDocuments, deleteDocument } from "@/lib/api";
import type { WSEvent } from "@/hooks/useWebSocket";

type Doc = { id: string; filename: string; status: string };

type Props = {
  selectedId: string | null;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  subscribe: (cb: (e: WSEvent) => void) => () => void;
};

export default function DocumentList({ selectedId, onSelect, onDelete, subscribe }: Props) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type !== "pipeline_event") return;
      if (event.event === "file_received") {
        fetchDocs();
      } else if (event.event === "processing_complete" && event.doc_id) {
        setDocs((prev) =>
          prev.map((d) => d.id === event.doc_id ? { ...d, status: "ready" } : d)
        );
      } else if (event.event === "processing_error" && event.doc_id) {
        setDocs((prev) =>
          prev.map((d) => d.id === event.doc_id ? { ...d, status: "error" } : d)
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

  useEffect(() => { fetchDocs(); }, []);

  const handleDelete = async (e: React.MouseEvent, doc: Doc) => {
    e.stopPropagation();
    if (!confirm(`Delete "${doc.filename}"?\nThis will remove all vectors from the database.`)) return;

    setDeletingId(doc.id);
    try {
      await deleteDocument(doc.id);
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
      if (selectedId === doc.id) onDelete?.(doc.id);
    } catch {
      alert("Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "ready":     return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
      case "processing": return <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />;
      default:          return <AlertCircle className="h-3.5 w-3.5 text-red-400" />;
    }
  };

  return (
    <div className="space-y-1.5">
      <h3 className="mb-3 px-1 text-xs font-semibold uppercase tracking-wider text-white/40">Documents</h3>
      {docs.length === 0 && <p className="px-1 text-xs text-white/25">No documents yet</p>}
      {docs.map((doc) => (
        <div
          key={doc.id}
          className={`group flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-all ${
            selectedId === doc.id
              ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-white border border-cyan-500/30"
              : "text-white/60 hover:bg-white/[0.06] hover:text-white/80 border border-transparent"
          }`}
        >
          {/* Clickable area */}
          <button
            onClick={() => doc.status === "ready" && onSelect(doc.id)}
            className={`flex flex-1 items-center gap-2.5 min-w-0 text-left ${
              doc.status !== "ready" ? "cursor-not-allowed opacity-60" : "cursor-pointer"
            }`}
          >
            <FileText className="h-4 w-4 shrink-0 text-white/40" />
            <span className="flex-1 truncate">{doc.filename}</span>
            {statusIcon(doc.status)}
          </button>

          {/* Delete button — visible on hover */}
          <button
            onClick={(e) => handleDelete(e, doc)}
            disabled={deletingId === doc.id}
            className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded-md hover:bg-red-500/20 text-white/30 hover:text-red-400 disabled:opacity-30"
            title="Delete document"
          >
            {deletingId === doc.id
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <Trash2 className="h-3.5 w-3.5" />
            }
          </button>
        </div>
      ))}
    </div>
  );
}
