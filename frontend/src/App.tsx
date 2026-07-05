import { useEffect, useState } from "react";
import { useBackend } from "./hooks/useBackend";
import { CommandBar } from "./components/CommandBar";
import { CoreColumn } from "./components/CoreColumn";
import { CommStream } from "./components/CommStream";
import { CommandInput } from "./components/CommandInput";
import { TaskMatrix } from "./components/TaskMatrix";
import { StatusStrip } from "./components/StatusStrip";
import type { PipelineState } from "./types";

export function App() {
  const {
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
  } = useBackend();

  // Backend durumu + son loglardan arayüz durum makinesi
  const [uiState, setUiState] = useState<PipelineState>("idle");
  useEffect(() => {
    if (!status.running) {
      setUiState("idle");
      return;
    }
    if (status.muted) {
      setUiState("muted");
      return;
    }
    const last = logs[logs.length - 1];
    if (!last) {
      setUiState("listening");
      return;
    }
    if (last.level === "user") {
      setUiState("transcribing");
      const t = setTimeout(() => setUiState("listening"), 900);
      return () => clearTimeout(t);
    }
    if (last.level === "jarvan") {
      setUiState("responding");
      const t = setTimeout(() => setUiState("listening"), 3500);
      return () => clearTimeout(t);
    }
    setUiState("listening");
  }, [status.running, status.muted, logs]);

  // Kısayollar: Ctrl+K başlat/durdur, M sustur
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const el = document.activeElement;
      const typing =
        el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" ||
          el.getAttribute("contenteditable") === "true");
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (status.running) stop();
        else start();
      } else if (e.key.toLowerCase() === "m" && !typing) {
        e.preventDefault();
        toggleMute(!status.muted);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [status.running, status.muted, start, stop, toggleMute]);

  // Bağlanınca pipeline'ı otomatik başlat
  useEffect(() => {
    if (connected && !status.running && !mockMode) start();
  }, [connected, status.running, mockMode, start]);

  return (
    <div className="blueprint flex h-full w-full flex-col bg-void font-body text-ink">
      <CommandBar connected={connected} />

      <div className="flex min-h-0 flex-1">
        {/* Sol: reaktör + vitals + kontroller */}
        <CoreColumn
          state={uiState}
          status={status}
          mode={mode}
          metrics={metrics}
          connected={connected || mockMode}
          onToggleLive={toggleLive}
          onToggleProactive={toggleProactive}
          onToggleMute={toggleMute}
        />

        {/* Merkez: konuşma-merkezli akış + komut girişi */}
        <main className="boot-2 flex min-w-[360px] flex-1 flex-col">
          <CommStream logs={logs} onClear={clearLogs} />
          <div className="shrink-0 border-t border-steel px-4 py-3">
            <CommandInput
              onSendMessage={sendTextMessage}
              muted={status.muted}
              onToggleMute={toggleMute}
              disabled={!connected && !mockMode}
            />
          </div>
        </main>

        {/* Sağ: ajan filosu görev matrisi */}
        <TaskMatrix tasks={tasks} onClear={clearTasks} />
      </div>

      <div className="boot-4">
        <StatusStrip
          logs={logs}
          metrics={metrics}
          mockMode={mockMode}
          connected={connected}
          onEnableMock={() => setMockMode(true)}
        />
      </div>
    </div>
  );
}
