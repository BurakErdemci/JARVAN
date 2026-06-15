import { useEffect, useMemo, useState } from "react";
import { Radio, Eye, ServerOff } from "lucide-react";
import { useBackend } from "./hooks/useBackend";
import { TitleBar } from "./components/TitleBar";
import { Hero } from "./components/Hero";
import { ToggleRow } from "./components/ToggleRow";
import { ChatArea } from "./components/ChatArea";
import { ChatInput } from "./components/ChatInput";
import { StatusBar } from "./components/StatusBar";
import { TaskPanel } from "./components/TaskPanel";
import { TaskDetail } from "./components/TaskDetail";
import { DemoController } from "./components/DemoController";
import { SystemDiagnostics } from "./components/SystemDiagnostics";
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
    simulateTask,
  } = useBackend();

  // Selected background task ID for details
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  // Active selected task object
  const selectedTask = useMemo(() => {
    return tasks.find((t) => t.id === selectedTaskId) || null;
  }, [tasks, selectedTaskId]);

  // Derive a UI state machine from the backend status, mute state, and logs
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
      const t = setTimeout(() => setUiState("listening"), 800);
      return () => clearTimeout(t);
    }
    if (last.level === "jarvan") {
      setUiState("responding");
      const t = setTimeout(() => setUiState("listening"), 3500);
      return () => clearTimeout(t);
    }
    setUiState("listening");
  }, [status.running, status.muted, logs]);

  // Subtitle feeds computation
  const lastUserMsg = useMemo(() => {
    const userLogs = logs.filter((l) => l.level === "user");
    return userLogs.length > 0 ? userLogs[userLogs.length - 1].text : "";
  }, [logs]);

  const lastJarvanMsg = useMemo(() => {
    const jarvanLogs = logs.filter((l) => l.level === "jarvan");
    return jarvanLogs.length > 0 ? jarvanLogs[jarvanLogs.length - 1].text : "";
  }, [logs]);

  // Keyboard Shortcuts:
  // 1. ⌘K / Ctrl+K to toggle pipeline start/stop
  // 2. M to toggle microphone mute (only if not typing in an input/textarea)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isTyping =
        activeEl &&
        (activeEl.tagName === "INPUT" ||
          activeEl.tagName === "TEXTAREA" ||
          activeEl.getAttribute("contenteditable") === "true");

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (status.running) stop();
        else start();
      } else if (e.key.toLowerCase() === "m" && !isTyping) {
        e.preventDefault();
        toggleMute(!status.muted);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [status.running, status.muted, start, stop, toggleMute]);

  // Auto-start (F1): If connected but pipeline isn't running, trigger start
  useEffect(() => {
    if (connected && !status.running && !mockMode) {
      start();
    }
  }, [connected, status.running, mockMode, start]);

  return (
    <div className="grain vignette grid-bg scanlines flex h-full w-full flex-col bg-obsidian text-ink overflow-hidden">
      {/* Universal TitleBar */}
      <TitleBar connected={connected} />

      {/* Main 3-Column Immersive Dashboard */}
      <div className="flex flex-1 min-h-0 relative">
        
        {/* Column 1: System Performance Diagnostics (Left - 22%) */}
        <div className="w-[260px] shrink-0 border-r border-hairline/80 h-full bg-surface-sunken/25">
          <SystemDiagnostics connected={connected} mockMode={mockMode} mode={mode} metrics={metrics} />
        </div>

        {/* Column 2: Assistant Voice & Chat Core (Center - 48%) */}
        <div className="flex h-full flex-1 flex-col border-r border-hairline/80 min-w-[380px] overflow-hidden">
          {/* Main Visualizer Core */}
          <Hero
            state={uiState}
            mode={mode}
            live={status.live}
            lastUserMsg={lastUserMsg}
            lastJarvanMsg={lastJarvanMsg}
          />

          {/* Settings Row */}
          <div className="px-4 py-1 space-y-1.5 shrink-0">
            <ToggleRow
              label="Live Mode"
              caption="Yerel ses motoru (Whisper + Gemma + Kokoro)"
              enabled={status.live}
              accent="pink"
              disabled={!connected}
              icon={<Radio size={13} strokeWidth={2} />}
              onToggle={toggleLive}
            />
            <ToggleRow
              label="Proaktif Bakış"
              caption="Ekran durumunu periyodik analiz eder"
              enabled={status.proactive}
              accent="amber"
              disabled={!connected}
              icon={<Eye size={13} strokeWidth={2} />}
              onToggle={toggleProactive}
            />
          </div>

          {/* Conversational speech bubble area */}
          <div className="flex-1 min-h-0 px-4 py-3 flex flex-col">
            <ChatArea logs={logs} onClear={clearLogs} />
          </div>

          {/* Developer simulation controls */}
          {!connected && !mockMode ? (
            <div className="mx-4 mb-2 flex items-center justify-between gap-3 rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-2 font-mono text-[9.5px] text-red-400">
              <div className="flex flex-row items-center gap-1.5">
                <ServerOff size={12} />
                <span>Backend çevrimdışı.</span>
              </div>
              <button
                onClick={() => setMockMode(true)}
                className="rounded border border-red-400/30 px-2 py-0.5 hover:bg-red-400/10 font-semibold"
              >
                Simülasyonu Aç
              </button>
            </div>
          ) : (
            <DemoController
              mockMode={mockMode}
              setMockMode={setMockMode}
              simulateTask={simulateTask}
              onSendMessage={sendTextMessage}
            />
          )}

          {/* Written input box */}
          <div className="px-4 pb-3 pt-1 shrink-0">
            <ChatInput
              onSendMessage={sendTextMessage}
              muted={status.muted}
              onToggleMute={toggleMute}
              disabled={!connected}
            />
          </div>
        </div>

        {/* Column 3: Agent Task Board & Detailed Logs (Right - 30%) */}
        <div className="w-[360px] shrink-0 h-full flex flex-col bg-surface-sunken/15">
          {selectedTask ? (
            <TaskDetail task={selectedTask} onClose={() => setSelectedTaskId(null)} />
          ) : (
            <TaskPanel
              tasks={tasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={setSelectedTaskId}
            />
          )}
        </div>
      </div>

      {/* Universal footer StatusBar */}
      <StatusBar connected={connected} />
    </div>
  );
}
