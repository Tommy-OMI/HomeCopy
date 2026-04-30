import { app, BrowserWindow, shell } from 'electron';
import { join } from 'node:path';
import { handleExternalAuthUrl, registerProtocol } from './services/auth';
import { getDatabase } from './services/database';
import { registerIpcHandlers } from './services/ipc';
import { startSyncWatcher } from './services/sync';

let mainWindow: BrowserWindow | null = null;
const gotSingleInstanceLock = app.requestSingleInstanceLock();

if (!gotSingleInstanceLock) {
  app.quit();
}

const createMainWindow = (): void => {
  mainWindow = new BrowserWindow({
    width: 1512,
    height: 982,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: '#070b14',
    title: 'OMI Astera',
    autoHideMenuBar: true,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }
};

app.whenReady().then(() => {
  registerProtocol();
  getDatabase();
  registerIpcHandlers();
  startSyncWatcher();
  createMainWindow();
});

app.on('second-instance', (_event, argv) => {
  const callbackUrl = argv.find((item) => item.startsWith('omiastro://auth') || item.startsWith('https://www.omiastro.com/_functions/authCallback'));
  if (callbackUrl) {
    handleExternalAuthUrl(callbackUrl);
  }

  if (mainWindow) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.focus();
  }
});

app.on('window-all-closed', () => {
  app.quit();
});
