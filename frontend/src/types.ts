export type PipelineState =
  | "idle"
  | "listening"
  | "transcribing"
  | "responding"
  | "muted";

export type ModeName = "unreal" | "unity" | "code" | "default";

export type LogLevel = "user" | "jarvan" | "system" | "error";

export interface LogEntry {
  id: string;
  level: LogLevel;
  text: string;
  timestamp: number;
  provider?: string;
}

export interface BackendStatus {
  running: boolean;
  live: boolean;
  proactive: boolean;
  muted: boolean;
}

export interface SystemMetrics {
  cpu: number;          // CPU kullanımı %
  ram_used: number;     // GB
  ram_total: number;    // GB
  ram_pct: number;      // %
  vram_used: number;    // GB (Ollama modelinin VRAM'i)
  vram_total: number;   // GB
  model_loaded: boolean;
}

export type TaskStatus = "queued" | "running" | "blocked" | "done" | "error";
export type TaskTarget = "codex" | "agy" | "claude" | "local" | "gemma";

export interface TaskStep {
  ts: number;
  text: string;
}

export interface TaskInfo {
  id: string;
  title: string;
  target: TaskTarget;
  status: TaskStatus;
  detail?: string;
  steps?: TaskStep[];
  error?: string | null;
  result?: string | null;
  created_at: number;
  updated_at: number;
}

export interface JarvanBridge {
  minimize: () => void;
  hide: () => void;
  close: () => void;
  toggleAlwaysOnTop: () => Promise<boolean>;
}

declare global {
  interface Window {
    jarvan: JarvanBridge;
  }
}
