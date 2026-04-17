import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("jarvan", {
  minimize: () => ipcRenderer.send("window:minimize"),
  hide: () => ipcRenderer.send("window:hide"),
  close: () => ipcRenderer.send("window:close"),
  toggleAlwaysOnTop: () => ipcRenderer.invoke("window:toggle-always-on-top"),
});
