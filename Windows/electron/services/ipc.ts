import { BrowserWindow, ipcMain } from 'electron';
import { getAuthState, logout, openLoginWindow } from './auth';
import { activateLicense, chooseDropboxAssociation, confirmDetectedDropboxAssociation, getLicenseState, getStartupChecks } from './license';
import { createProcessingJobFromIndex, listProcessingJobs } from './processing';
import { createProject, getDashboardState, openProject, revealCurrentProject } from './projects';
import { getSyncState, rescanSyncFiles, revealSyncFolder } from './sync';
import type { ActivateLicenseInput } from './license';
import type { CreateProjectInput } from './types';

export const registerIpcHandlers = (): void => {
  ipcMain.handle('auth:get-state', () => getAuthState());
  ipcMain.handle('auth:login', (event) => openLoginWindow(BrowserWindow.fromWebContents(event.sender)));
  ipcMain.handle('auth:logout', () => logout());
  ipcMain.handle('license:get-state', () => getLicenseState());
  ipcMain.handle('license:activate', (_event, input: ActivateLicenseInput) => activateLicense(input));
  ipcMain.handle('license:choose-dropbox-association', () => chooseDropboxAssociation());
  ipcMain.handle('license:confirm-detected-dropbox', () => confirmDetectedDropboxAssociation());
  ipcMain.handle('startup:get-checks', () => getStartupChecks());
  ipcMain.handle('dashboard:get-state', () => getDashboardState());
  ipcMain.handle('projects:create', (_event, input: CreateProjectInput) => createProject(input));
  ipcMain.handle('projects:open', () => openProject());
  ipcMain.handle('projects:reveal-current', () => revealCurrentProject());
  ipcMain.handle('processing:list-jobs', () => listProcessingJobs());
  ipcMain.handle('processing:create-from-index', () => createProcessingJobFromIndex());
  ipcMain.handle('sync:get-state', () => getSyncState());
  ipcMain.handle('sync:rescan-files', () => rescanSyncFiles());
  ipcMain.handle('sync:reveal-folder', (_event, targetPath?: string) => revealSyncFolder(targetPath));
};
