export type PipelineState =
  | "idle"
  | "listening"
  | "transcribing"
  | "responding";

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
