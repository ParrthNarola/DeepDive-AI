"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export type WSEvent = {
  type: string;
  [key: string]: unknown;
};

type Subscriber = (event: WSEvent) => void;

export function useWebSocket(url: string = "ws://localhost:8000/ws") {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const subscribersRef = useRef<Set<Subscriber>>(new Set());
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  // Track whether the user manually disconnected (no auto-reconnect)
  const manualDisconnect = useRef(false);

  const connect = useCallback(() => {
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) return;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnected(true);
      manualDisconnect.current = false;
      console.log("[WS] Connected");
    };

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data);
        subscribersRef.current.forEach((cb) => cb(data));
      } catch (e) {
        console.warn("[WS] Failed to parse message:", event.data);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (!manualDisconnect.current) {
        console.log("[WS] Disconnected — reconnecting in 2s…");
        reconnectTimeout.current = setTimeout(connect, 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const reconnect = useCallback(() => {
    if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    manualDisconnect.current = false;
    if (wsRef.current) {
      manualDisconnect.current = true; // suppress auto-reconnect from the close event
      wsRef.current.close();
      manualDisconnect.current = false;
    }
    connect();
  }, [connect]);

  const subscribe = useCallback((callback: Subscriber) => {
    subscribersRef.current.add(callback);
    return () => {
      subscribersRef.current.delete(callback);
    };
  }, []);

  return { connected, subscribe, reconnect };
}
