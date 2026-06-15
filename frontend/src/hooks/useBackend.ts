import { useCallback, useEffect, useRef, useState } from "react";
import type { BackendStatus, LogEntry, ModeName, TaskInfo, TaskStatus, TaskTarget, SystemMetrics } from "../types";

const WS_URL = "ws://127.0.0.1:8765/ws";
const RECONNECT_DELAY = 2000;
const MAX_LOGS = 200;

export function useBackend() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const mockTimeoutRefs = useRef<number[]>([]);

  const [connected, setConnected] = useState(false);
  const [mockMode, setMockModeState] = useState(() => {
    return localStorage.getItem("jarvan_mock_mode") === "true";
  });

  const [status, setStatus] = useState<BackendStatus>({
    running: false,
    live: false,
    proactive: false,
    muted: false,
  });
  const [mode, setMode] = useState<ModeName>("default");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);

  const setMockMode = useCallback((val: boolean) => {
    localStorage.setItem("jarvan_mock_mode", String(val));
    setMockModeState(val);
    if (val) {
      setConnected(true);
      setStatus({
        running: true,
        live: true,
        proactive: false,
        muted: false,
      });
      setMode("code");
      setLogs([
        {
          id: crypto.randomUUID(),
          level: "system",
          text: "Demo/Simülasyon Modu Aktif. Sesli ve yazılı komutları deneyebilirsiniz.",
          timestamp: Date.now(),
        },
      ]);
    } else {
      setConnected(false);
      setLogs([]);
      setTasks([]);
      // Trigger reconnection to actual server
      window.location.reload();
    }
  }, []);

  // Clear mock timeouts
  const clearMockTimeouts = useCallback(() => {
    mockTimeoutRefs.current.forEach((t) => window.clearTimeout(t));
    mockTimeoutRefs.current = [];
  }, []);

  // WebSocket Connection
  const connect = useCallback(() => {
    if (mockMode) {
      setConnected(true);
      return;
    }

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
            muted: !!msg.muted,
          });

          // Auto-start feature (F1): if backend says running is false, and we are connected, auto send start
          if (!msg.running) {
            ws.send(JSON.stringify({ type: "start" }));
          }
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
        } else if (msg.type === "task") {
          const incomingTask = msg.task as TaskInfo;
          if (incomingTask && incomingTask.id) {
            setTasks((prev) => {
              const idx = prev.findIndex((t) => t.id === incomingTask.id);
              if (idx > -1) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...incomingTask, updated_at: Date.now() };
                return updated;
              } else {
                return [...prev, { ...incomingTask, created_at: Date.now(), updated_at: Date.now() }];
              }
            });
          }
        } else if (msg.type === "metrics") {
          setMetrics({
            cpu: msg.cpu ?? 0,
            ram_used: msg.ram_used ?? 0,
            ram_total: msg.ram_total ?? 0,
            ram_pct: msg.ram_pct ?? 0,
            vram_used: msg.vram_used ?? 0,
            vram_total: msg.vram_total ?? 0,
            model_loaded: !!msg.model_loaded,
          });
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
  }, [mockMode]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
      clearMockTimeouts();
    };
  }, [connect, clearMockTimeouts]);

  const send = useCallback(
    (payload: Record<string, unknown>) => {
      if (mockMode) return;
      const ws = wsRef.current;
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload));
      }
    },
    [mockMode]
  );

  // Core actions
  const start = useCallback(() => {
    if (mockMode) {
      setStatus((prev) => ({ ...prev, running: true }));
    } else {
      send({ type: "start" });
    }
  }, [send, mockMode]);

  const stop = useCallback(() => {
    if (mockMode) {
      setStatus((prev) => ({ ...prev, running: false }));
    } else {
      send({ type: "stop" });
    }
  }, [send, mockMode]);

  const toggleLive = useCallback(
    (enabled: boolean) => {
      if (mockMode) {
        setStatus((prev) => ({ ...prev, live: enabled }));
      } else {
        send({ type: "toggle_live", enabled });
      }
    },
    [send, mockMode]
  );

  const toggleProactive = useCallback(
    (enabled: boolean) => {
      if (mockMode) {
        setStatus((prev) => ({ ...prev, proactive: enabled }));
      } else {
        send({ type: "toggle_proactive", enabled });
      }
    },
    [send, mockMode]
  );

  const toggleMute = useCallback(
    (enabled: boolean) => {
      if (mockMode) {
        setStatus((prev) => ({ ...prev, muted: enabled }));
        setLogs((prevLogs) => [
          ...prevLogs,
          {
            id: crypto.randomUUID(),
            level: "system",
            text: enabled ? "Mikrofon susturuldu." : "Mikrofon aktif.",
            timestamp: Date.now(),
          },
        ]);
      } else {
        send({ type: "mute", enabled });
      }
    },
    [send, mockMode]
  );

  // Mock simulation runner helper
  const addMockTimeout = (fn: () => void, ms: number) => {
    const t = window.setTimeout(fn, ms);
    mockTimeoutRefs.current.push(t);
  };

  const simulateTaskMock = useCallback((type: "done" | "blocked" | "error") => {
    const taskId = crypto.randomUUID().slice(0, 8);
    let title = "Kod Refaktörü";
    let target: TaskTarget = "codex";
    if (type === "blocked") {
      title = "Paket Kurulumu";
      target = "local";
    } else if (type === "error") {
      title = "Hata Log Analizi";
      target = "agy";
    }

    const initialTask: TaskInfo = {
      id: taskId,
      title,
      target,
      status: "queued",
      detail: "İşlem sıraya alındı...",
      steps: [{ ts: Date.now(), text: "Görev ajana gönderildi." }],
      created_at: Date.now(),
      updated_at: Date.now(),
    };

    setTasks((prev) => [initialTask, ...prev]);

    // Transition to Running
    addMockTimeout(() => {
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? {
                ...t,
                status: "running",
                detail: "Dosyalar taranıyor...",
                steps: [...(t.steps || []), { ts: Date.now(), text: "Dosya ağacı analiz ediliyor." }],
                updated_at: Date.now(),
              }
            : t
        )
      );
    }, 1200);

    // Transition to Running Step 2
    addMockTimeout(() => {
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? {
                ...t,
                detail: type === "blocked" ? "npm install --save lodash..." : "İşlem yürütülüyor...",
                steps: [
                  ...(t.steps || []),
                  { ts: Date.now(), text: type === "blocked" ? "Bağımlılıklar indiriliyor." : "Kod semantiği inceleniyor." },
                ],
                updated_at: Date.now(),
              }
            : t
        )
      );
    }, 3000);

    // Final outcome
    addMockTimeout(() => {
      setTasks((prev) =>
        prev.map((t) => {
          if (t.id !== taskId) return t;
          if (type === "done") {
            return {
              ...t,
              status: "done",
              detail: "Başarıyla tamamlandı.",
              steps: [...(t.steps || []), { ts: Date.now(), text: "Değişiklikler uygulandı ve doğrulandı." }],
              result: "```javascript\n// Refactored helper function\nexport function calculateGlow(amplitude, factor) {\n  const base = Math.max(3, amplitude * 100);\n  return base * factor + Math.sin(Date.now() / 1000);\n}\n```\n\n**Değişiklikler:**\n- `Math.max` koruması eklendi.\n- Zaman bazlı sinüs dalgası sönümlemesi eklendi.\n- Bellek sızıntısı giderildi.",
              updated_at: Date.now(),
            };
          } else if (type === "blocked") {
            return {
              ...t,
              status: "blocked",
              detail: "Çakışma Sorunu",
              error: "Peer dependency çakışması: React 18 ile uyumsuz paket. Devam etmek için --legacy-peer-deps bayrağı gerekebilir.",
              steps: [
                ...(t.steps || []),
                { ts: Date.now(), text: "npm CLI çakışma hatası verdi." },
              ],
              updated_at: Date.now(),
            };
          } else {
            return {
              ...t,
              status: "error",
              detail: "Derleme Hatası",
              error: "TypeError: Cannot read properties of undefined (reading 'map') at Line 42 in index.tsx",
              steps: [
                ...(t.steps || []),
                { ts: Date.now(), text: "Test derleme aşamasında hata alındı." },
              ],
              updated_at: Date.now(),
            };
          }
        })
      );

      // System notification log
      setLogs((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          level: "system",
          text: `Görev [${title}] durumu güncellendi: ${
            type === "done" ? "Tamamlandı" : type === "blocked" ? "Takıldı" : "Hata Alındı"
          }`,
          timestamp: Date.now(),
        },
      ]);
    }, 5000);
  }, []);

  // Text message sender (handles Mock responses too)
  const sendTextMessage = useCallback(
    (text: string) => {
      if (!text.trim()) return;

      const userLog: LogEntry = {
        id: crypto.randomUUID(),
        level: "user",
        text: text,
        timestamp: Date.now(),
      };

      setLogs((prev) => [...prev, userLog]);

      if (mockMode) {
        // Mock Response simulation
        addMockTimeout(() => {
          // Add system feedback "thinking" implicitly by showing "Jarvan is responding..."
          const lowerText = text.toLowerCase();
          let responseText = "Anladım. Sizin için araştırıyorum.";

          if (lowerText.includes("selam") || lowerText.includes("merhaba")) {
            responseText = "Merhaba Burak! Ben Jarvan. Kontrol merkezimiz tamamen güncellendi. Nasıl yardımcı olabilirim?";
          } else if (lowerText.includes("kod") || lowerText.includes("refactor")) {
            responseText = "Anlaşıldı, kod refaktörü işlemini başlatıyorum. Durumu task panelinden canlı izleyebilirsiniz.";
            simulateTaskMock("done");
          } else if (lowerText.includes("hata") || lowerText.includes("hata simüle et")) {
            responseText = "Hata analizi görevini başlatıyorum.";
            simulateTaskMock("error");
          } else if (lowerText.includes("takıl") || lowerText.includes("blok")) {
            responseText = "Bloke durumlu bir kurulum görevi simüle ediliyor...";
            simulateTaskMock("blocked");
          } else if (lowerText.includes("temizle")) {
            setLogs([]);
            setTasks([]);
            return;
          }

          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              level: "jarvan",
              text: responseText,
              timestamp: Date.now(),
            },
          ]);
        }, 1000);
      } else {
        send({ type: "text", text });
      }
    },
    [send, mockMode, simulateTaskMock]
  );

  const clearLogs = useCallback(() => setLogs([]), []);
  const clearTasks = useCallback(() => setTasks([]), []);

  return {
    connected,
    mockMode,
    setMockMode,
    status,
    mode,
    logs,
    tasks,
    metrics,
    start,
    stop,
    toggleLive,
    toggleProactive,
    toggleMute,
    sendTextMessage,
    clearLogs,
    clearTasks,
    simulateTask: simulateTaskMock,
  };
}
