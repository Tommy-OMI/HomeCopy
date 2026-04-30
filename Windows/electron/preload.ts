import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('omiAstera', {
  appName: 'OMI Astera',
  platform: process.platform,
  getAuthState: () => ipcRenderer.invoke('auth:get-state'),
  login: () => ipcRenderer.invoke('auth:login'),
  logout: () => ipcRenderer.invoke('auth:logout'),
  getLicenseState: () => ipcRenderer.invoke('license:get-state'),
  activateLicense: (input: unknown) => ipcRenderer.invoke('license:activate', input),
  chooseDropboxAssociation: () => ipcRenderer.invoke('license:choose-dropbox-association'),
  confirmDetectedDropboxAssociation: () => ipcRenderer.invoke('license:confirm-detected-dropbox'),
  getStartupChecks: () => ipcRenderer.invoke('startup:get-checks'),
  getDashboardState: () => ipcRenderer.invoke('dashboard:get-state'),
  createProject: (input: unknown) => ipcRenderer.invoke('projects:create', input),
  openProject: () => ipcRenderer.invoke('projects:open'),
  revealCurrentProject: () => ipcRenderer.invoke('projects:reveal-current'),
  listProcessingJobs: () => ipcRenderer.invoke('processing:list-jobs'),
  createProcessingJobFromIndex: () => ipcRenderer.invoke('processing:create-from-index'),
  getSyncState: () => ipcRenderer.invoke('sync:get-state'),
  rescanSyncFiles: () => ipcRenderer.invoke('sync:rescan-files'),
  revealSyncFolder: (targetPath?: string) => ipcRenderer.invoke('sync:reveal-folder', targetPath)
});
