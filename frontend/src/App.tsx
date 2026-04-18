import { useEffect, useMemo, useState } from "react";
import { Radio, Eye } from "lucide-react";
import { useBackend } from "./hooks/useBackend";
import { TitleBar } from "./components/TitleBar";
import { Hero } from "./components/Hero";
import { PrimaryButton } from "./components/PrimaryButton";
import { ToggleRow } from "./components/ToggleRow";
import { LogPanel } from "./components/LogPanel";
import { StatusBar } from "./components/StatusBar";
import type { PipelineState } from "./types";

export function App() {
  const {
    connected,
    status,
    mode,
    logs,
    start,
    stop,
    toggleLive,
    toggleProactive,
    clearLogs,
  } = useBackend();

  // Derive a UI state machine from the latest log events
  const [uiState, setUiState] = useState<PipelineState>("idle");

  useEffect(() => {
    if (!status.running) {
      setUiState("idle");
      return;
    }
    const last = logs[logs.length - 1];
    if (!last) {
      setUiState("listening");
      return;
    }

    if (last.level === "user") {
      setUiState("transcribing");
      const t = setTimeout(() => setUiState("listening"), 250);
      return () => clearTimeout(t);
    }
    if (last.level === "jarvan") {
      setUiState("responding");
      const t = setTimeout(() => setUiState("listening"), 3500);
      return () => clearTimeout(t);
    }
    setUiState("listening");
  }, [status.running, logs]);

  // Keyboard: ⌘K / Ctrl+K to toggle pipeline
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (status.running) stop();
        else start();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [status.running, start, stop]);

  const primaryClick = useMemo(
    () => (status.running ? stop : start),
    [status.running, start, stop]
  );

  return (
    <div className="grain vignette flex h-full w-full flex-col bg-obsidian text-ink">
      <TitleBar connected={connected} />

      <Hero state={uiState} mode={mode} live={status.live} />

      {/* Primary control + toggles */}
      <div className="space-y-2 px-4">
        <PrimaryButton
          running={status.running}
          disabled={!connected}
          onClick={primaryClick}
        />

        <div className="space-y-1.5">
          <ToggleRow
            label="Live"
            caption="Gemini native ses — ekran paylaşımı yok"
            enabled={status.live}
            accent="pink"
            disabled={!connected}
            icon={<Radio size={13} strokeWidth={2} />}
            onToggle={toggleLive}
          />
          <ToggleRow
            label="Proaktif"
            caption="'Bak / ekran / şurda' dediğinde ekran analizi"
            enabled={status.proactive}
            accent="amber"
            disabled={!connected}
            icon={<Eye size={13} strokeWidth={2} />}
            onToggle={toggleProactive}
          />
        </div>
      </div>

      {/* Log panel */}
      <div className="flex min-h-0 flex-1 flex-col px-4 pb-3 pt-3">
        <LogPanel logs={logs} onClear={clearLogs} />
      </div>

      <StatusBar connected={connected} />
    </div>
  );
}
