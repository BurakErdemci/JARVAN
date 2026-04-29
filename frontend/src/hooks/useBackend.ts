import { useCallback, useEffect, useRef, useState } from "react";
import type { BackendStatus, LogEntry, ModeName } from "../types";

const WS_URL = "ws://127.0.0.1:8765/ws";
const RECONNECT_DELAY = 2000;
const MAX_LOGS = 200;

export function useBackend() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<BackendStatus>({
    running: false,
    live: false,
    proactive: false,
  });
  const [mode, setMode] = useState<ModeName>("default");
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setLogs((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          level: "system",
          text: "Backend bağlandı",
          timestamp: Date.now(),
        },
      ]);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "status") {
          setStatus({
            running: !!msg.running,
            live: !!msg.live,
            proactive: !!msg.proactive,
          });
        } else if (msg.type === "mode") {
          const name = (msg.name || "default") as ModeName;
          setMode(name);
        } else if (msg.type === "log") {
          setLogs((prev) => {
            const next: LogEntry = {
              id: crypto.randomUUID(),
              level: msg.level || "system",
              text: msg.text || "",
              timestamp: Date.now(),
              provider: msg.provider,
            };
            const combined = [...prev, next];
            return combined.length > MAX_LOGS
              ? combined.slice(combined.length - MAX_LOGS)
              : combined;
          });
        } else if (msg.type === "window_hide") {
          window.jarvan?.hide();
        }
      } catch (e) {
        console.error("WS parse error:", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = window.setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }, []);

  const start = useCallback(() => send({ type: "start" }), [send]);
  const stop = useCallback(() => send({ type: "stop" }), [send]);
  const toggleLive = useCallback(
    (enabled: boolean) => send({ type: "toggle_live", enabled }),
    [send]
  );
  const toggleProactive = useCallback(
    (enabled: boolean) => send({ type: "toggle_proactive", enabled }),
    [send]
  );
  const clearLogs = useCallback(() => setLogs([]), []);

  return {
    connected,
    status,
    mode,
    logs,
    start,
    stop,
    toggleLive,
    toggleProactive,
    clearLogs,
  };
}
