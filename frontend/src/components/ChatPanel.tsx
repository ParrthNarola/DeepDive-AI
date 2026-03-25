"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send, Bot, User, Sparkles, BookOpen } from "lucide-react";
import { sendChatMessage } from "@/lib/api";
import type { WSEvent } from "@/hooks/useWebSocket";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Message = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

type ChunkTrace = {
  index: number;
  page: string | number;
  snippet: string;
};

type Props = {
  documentId: string | null;
  subscribe: (cb: (e: WSEvent) => void) => () => void;
};

let msgId = 0;

export default function ChatPanel({ documentId, subscribe }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamTokens, setStreamTokens] = useState("");
  const [thinking, setThinking] = useState(false);
  const [traces, setTraces] = useState<ChunkTrace[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Subscribe to LLM streaming / trace events
  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type === "llm_token") {
        setStreamTokens((prev) => prev + (event.token as string));
      }
      if (event.type === "pipeline_event" && event.event === "llm_start") {
        setThinking(true);
        setStreamTokens("");
      }
      if (event.type === "pipeline_event" && event.event === "llm_end") {
        setThinking(false);
      }
      if (event.type === "pipeline_event" && event.event === "retriever_end") {
        setTraces((event.chunks as ChunkTrace[]) || []);
      }
    });
    return unsub;
  }, [subscribe]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamTokens]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || !documentId || loading) return;

    const userMsg: Message = { id: msgId++, role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setStreamTokens("");
    setTraces([]);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const result = await sendChatMessage(userMsg.content, documentId, history);
      setMessages((prev) => [...prev, { id: msgId++, role: "assistant", content: result.answer }]);
      setStreamTokens("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setMessages((prev) => [
        ...prev,
        { id: msgId++, role: "assistant", content: `⚠️ ${msg}` },
      ]);
    } finally {
      setLoading(false);
      setThinking(false);
    }
  }, [input, documentId, loading, messages]);

  return (
    <div className="flex h-full flex-col rounded-2xl border border-white/10 bg-black/40 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <Sparkles className="h-4 w-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-white/80">Research Chat</h3>
        {documentId && (
          <span className="ml-auto rounded-full bg-cyan-500/20 px-2 py-0.5 text-[10px] font-medium text-cyan-400">
            {documentId}
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!documentId && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-white/30">Upload and process a document to start chatting</p>
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/30 to-purple-500/30">
                <Bot className="h-4 w-4 text-cyan-400" />
              </div>
            )}
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-gradient-to-r from-cyan-600/80 to-blue-600/80 text-white"
                  : "bg-white/[0.06] text-white/80"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="prose prose-sm prose-invert max-w-none
                  prose-headings:text-white/90 prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1
                  prose-p:my-1 prose-p:leading-relaxed
                  prose-strong:text-cyan-300 prose-strong:font-semibold
                  prose-code:text-amber-300 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
                  prose-ul:my-1 prose-ul:pl-4 prose-li:my-0.5
                  prose-ol:my-1 prose-ol:pl-4
                  prose-blockquote:border-cyan-500/50 prose-blockquote:text-white/60">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
            </div>
            {msg.role === "user" && (
              <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-600/40 to-blue-600/40">
                <User className="h-4 w-4 text-white/60" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming tokens */}
        {loading && streamTokens && (
          <div className="flex gap-3">
            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500/30 to-purple-500/30">
              <Bot className="h-4 w-4 text-cyan-400" />
            </div>
            <div className="max-w-[80%] rounded-2xl bg-white/[0.06] px-4 py-2.5 text-sm leading-relaxed text-white/80">
              <div className="prose prose-sm prose-invert max-w-none
                prose-headings:text-white/90 prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1
                prose-p:my-1 prose-strong:text-cyan-300 prose-strong:font-semibold
                prose-code:text-amber-300 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
                prose-ul:my-1 prose-ul:pl-4 prose-li:my-0.5 prose-ol:my-1 prose-ol:pl-4">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamTokens}</ReactMarkdown>
              </div>
              <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-cyan-400" />
            </div>
          </div>
        )}

        {/* Thinking indicator */}
        {thinking && !streamTokens && (
          <div className="flex items-center gap-2 text-xs text-white/40">
            <div className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-400 [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-400 [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-400 [animation-delay:300ms]" />
            </div>
            Thinking…
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Thinking trace — chunk citations */}
      {traces.length > 0 && (
        <div className="border-t border-white/10 px-4 py-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-white/50">
            <BookOpen className="h-3 w-3" />
            Sources Referenced
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {traces.map((t) => (
              <div
                key={t.index}
                className="shrink-0 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs"
              >
                <span className="font-medium text-cyan-400">Page {t.page}</span>
                <p className="mt-1 max-w-[200px] truncate text-white/40">{t.snippet}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 focus-within:border-cyan-500/50 transition-colors">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder={documentId ? "Ask about your document…" : "Upload a document first"}
            disabled={!documentId || loading}
            className="flex-1 bg-transparent text-sm text-white/80 placeholder-white/30 outline-none disabled:cursor-not-allowed"
          />
          <button
            onClick={handleSend}
            disabled={!documentId || loading || !input.trim()}
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 text-white transition-all hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/25 disabled:opacity-30 disabled:hover:scale-100"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
