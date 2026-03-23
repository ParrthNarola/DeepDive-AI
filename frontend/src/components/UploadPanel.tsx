"use client";

import { useCallback, useState } from "react";
import { Upload, FileText, Loader2, CheckCircle2 } from "lucide-react";
import { uploadDocument } from "@/lib/api";

type Props = {
  onUploaded?: (docId: string, filename: string) => void;
};

export default function UploadPanel({ onUploaded }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are supported");
        return;
      }
      setError(null);
      setUploading(true);
      setUploadedFile(null);

      try {
        const result = await uploadDocument(file);
        setUploadedFile(file.name);
        onUploaded?.(result.doc_id, file.name);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploaded]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`
        relative rounded-2xl border-2 border-dashed p-8 text-center transition-all duration-300
        ${
          dragging
            ? "border-cyan-400 bg-cyan-400/5 scale-[1.02] shadow-lg shadow-cyan-500/10"
            : "border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"
        }
      `}
    >
      <input
        type="file"
        accept=".pdf"
        onChange={onFileSelect}
        className="absolute inset-0 cursor-pointer opacity-0"
        disabled={uploading}
      />

      {uploading ? (
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-10 w-10 animate-spin text-cyan-400" />
          <p className="text-sm text-white/60">Uploading document…</p>
        </div>
      ) : uploadedFile ? (
        <div className="flex flex-col items-center gap-3">
          <CheckCircle2 className="h-10 w-10 text-emerald-400" />
          <p className="text-sm text-emerald-300">{uploadedFile} uploaded</p>
          <p className="text-xs text-white/40">Drop another file to replace</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <div className="rounded-xl bg-gradient-to-br from-cyan-500/20 to-purple-500/20 p-4">
            <Upload className="h-8 w-8 text-cyan-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-white/80">
              Drop a PDF here or <span className="text-cyan-400 underline underline-offset-2">browse</span>
            </p>
            <p className="mt-1 text-xs text-white/40">Supports PDF documents up to 50 MB</p>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
    </div>
  );
}
