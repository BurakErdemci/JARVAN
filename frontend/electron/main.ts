import { app, BrowserWindow, Tray, Menu, nativeImage, shell, ipcMain } from "electron";
import { spawn, ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const DIST = path.join(__dirname, "..");
const RENDERER_DIST = path.join(DIST, "dist");
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const BACKEND_DIR = path.join(PROJECT_ROOT, "backend");
process.env.APP_ROOT = path.join(__dirname, "..");
const VITE_DEV_SERVER_URL = process.env["VITE_DEV_SERVER_URL"];

let win: BrowserWindow | null = null;
let tray: Tray | null = null;
let backend: ChildProcess | null = null;
let quitting = false;

function resolvePythonExecutable(): string {
  const isWin = process.platform === "win32";
  const candidates = isWin
    ? [
        path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe"),
        path.join(PROJECT_ROOT, "backend", ".venv", "Scripts", "python.exe"),
      ]
    : [
        path.join(PROJECT_ROOT, ".venv", "bin", "python"),
        path.join(PROJECT_ROOT, "backend", ".venv", "bin", "python"),
      ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return isWin ? "python" : "python3";
}

function startBackend() {
  if (backend) return;
  const py = resolvePythonExecutable();
  console.log(`[backend] spawning: ${py} main.py (cwd=${BACKEND_DIR})`);
  backend = spawn(py, ["main.py"], {
    cwd: BACKEND_DIR,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });

  backend.stdout?.on("data", (d) => process.stdout.write(`[backend] ${d}`));
  backend.stderr?.on("data", (d) => process.stderr.write(`[backend] ${d}`));
  backend.on("exit", (code, signal) => {
    console.log(`[backend] exited code=${code} signal=${signal}`);
    backend = null;
  });
  backend.on("error", (err) => {
    console.error(`[backend] spawn error:`, err);
    backend = null;
  });
}

function stopBackend() {
  if (!backend) return;
  console.log("[backend] stopping...");
  try {
    if (process.platform === "win32") {
      backend.kill();
    } else {
      backend.kill("SIGTERM");
      setTimeout(() => backend && backend.kill("SIGKILL"), 3000);
    }
  } catch (e) {
    console.error("[backend] kill error:", e);
  }
  backend = null;
}

function createWindow() {
  win = new BrowserWindow({
    width: 420,
    height: 640,
    minWidth: 420,
    minHeight: 640,
    resizable: false,
    frame: false,
    transparent: false,
    backgroundColor: "#0b0b0e",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: -100, y: -100 },
    vibrancy: undefined,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.mjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.once("ready-to-show", () => win?.show());

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  win.on("close", (e) => {
    if (!quitting) {
      e.preventDefault();
      win?.hide();
    }
  });

  if (VITE_DEV_SERVER_URL) {
    win.loadURL(VITE_DEV_SERVER_URL);
  } else {
    win.loadFile(path.join(RENDERER_DIST, "index.html"));
  }
}

function createTray() {
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip("Jarvan");

  const menu = Menu.buildFromTemplate([
    {
      label: "Göster",
      click: () => win?.show(),
    },
    {
      label: "Gizle",
      click: () => win?.hide(),
    },
    { type: "separator" },
    {
      label: "Çık",
      click: () => {
        quitting = true;
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(menu);
  tray.on("click", () => {
    if (win?.isVisible()) win.hide();
    else win?.show();
  });
}

ipcMain.on("window:minimize", () => win?.minimize());
ipcMain.on("window:hide", () => win?.hide());
ipcMain.on("window:close", () => win?.hide());
ipcMain.handle("window:toggle-always-on-top", () => {
  if (!win) return false;
  const next = !win.isAlwaysOnTop();
  win.setAlwaysOnTop(next, "floating");
  return next;
});

app.whenReady().then(() => {
  startBackend();
  createWindow();
  createTray();
});

app.on("before-quit", () => {
  quitting = true;
  stopBackend();
});

app.on("will-quit", () => {
  stopBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
  else win?.show();
});
