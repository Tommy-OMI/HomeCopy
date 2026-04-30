import { app, shell } from 'electron';
import { existsSync, readdirSync, readFileSync, statSync, watch, type FSWatcher } from 'node:fs';
import { basename, join, resolve } from 'node:path';
import { getDatabase } from './database';

export type SyncFolderRecord = {
  name: string;
  path: string;
  folderCount: number;
  fitsCount: number;
  totalSizeBytes: number;
  updatedAt: string | null;
};

export type SyncState = {
  syncRoot: string | null;
  source: string;
  folders: SyncFolderRecord[];
  indexedFitsCount: number;
  stableFitsCount: number;
  lastIndexedAt: string | null;
};

const fitsExtensions = new Set(['.fit', '.fits']);
let syncWatcher: FSWatcher | null = null;
let watcherRoot: string | null = null;
let rescanTimer: NodeJS.Timeout | null = null;

export type SyncWatcherState = {
  running: boolean;
  root: string | null;
  lastEventAt: string | null;
};

let lastWatcherEventAt: string | null = null;

export const getSyncState = (): SyncState => {
  const syncRoot = getDropboxPath();

  if (!syncRoot) {
    return {
      syncRoot: null,
      source: 'Dropbox folder not detected',
      folders: [],
      indexedFitsCount: 0,
      stableFitsCount: 0,
      lastIndexedAt: null
    };
  }

  const folders = safeReadDir(syncRoot)
    .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.'))
    .map((entry) => scanFolder(join(syncRoot, entry.name)))
    .sort((a, b) => a.name.localeCompare(b.name));

  return {
    syncRoot,
    source: 'Detected local Dropbox sync folder',
    folders,
    ...getIndexSummary()
  };
};

export const rescanSyncFiles = (): SyncState => {
  const state = getSyncState();
  if (!state.syncRoot) {
    return state;
  }

  const now = new Date().toISOString();
  const files = collectFitsFiles(state.syncRoot);
  const db = getDatabase();
  const existingRows = db.prepare('SELECT path, size_bytes, status, detected_at, stable_at FROM sync_files').all() as Array<{
    path: string;
    size_bytes: number;
    status: string;
    detected_at: string;
    stable_at: string | null;
  }>;
  const existing = new Map(existingRows.map((row) => [row.path, row]));

  const upsert = db.prepare(`
    INSERT INTO sync_files (
      path, folder_path, folder_name, file_name, extension, size_bytes, status, detected_at, stable_at, synced_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
    ON CONFLICT(path) DO UPDATE SET
      folder_path = excluded.folder_path,
      folder_name = excluded.folder_name,
      file_name = excluded.file_name,
      extension = excluded.extension,
      size_bytes = excluded.size_bytes,
      status = excluded.status,
      stable_at = excluded.stable_at,
      updated_at = excluded.updated_at
  `);

  const seen = new Set<string>();
  for (const file of files) {
    seen.add(file.path);
    const previous = existing.get(file.path);
    const isStable = Boolean(previous && previous.size_bytes === file.sizeBytes);
    const status = isStable ? 'stable' : 'detected';
    const detectedAt = previous?.detected_at ?? now;
    const stableAt = isStable ? previous?.stable_at ?? now : null;
    upsert.run(file.path, file.folderPath, basename(file.folderPath), file.fileName, file.extension, file.sizeBytes, status, detectedAt, stableAt, now);
  }

  const remove = db.prepare('DELETE FROM sync_files WHERE path = ?');
  for (const row of existingRows) {
    if (!seen.has(row.path)) {
      remove.run(row.path);
    }
  }

  db.prepare('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)').run('INFO', `FITS rescan indexed ${files.length} files`, now);
  return getSyncState();
};

export const startSyncWatcher = (): SyncWatcherState => {
  const state = getSyncState();
  if (!state.syncRoot) {
    stopSyncWatcher();
    return getSyncWatcherState();
  }

  if (syncWatcher && watcherRoot === state.syncRoot) {
    return getSyncWatcherState();
  }

  stopSyncWatcher();
  watcherRoot = state.syncRoot;
  try {
    syncWatcher = watch(state.syncRoot, { recursive: true }, (_eventType, fileName) => {
      if (!fileName || !isFitsName(String(fileName))) {
        return;
      }

      lastWatcherEventAt = new Date().toISOString();
      if (rescanTimer) {
        clearTimeout(rescanTimer);
      }
      rescanTimer = setTimeout(() => {
        try {
          rescanSyncFiles();
        } catch {
          // Watcher errors should not bring down the desktop app.
        }
      }, 1500);
    });

    getDatabase().prepare('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)').run('INFO', `Local Agent watching ${state.syncRoot}`, new Date().toISOString());
  } catch {
    watcherRoot = null;
    syncWatcher = null;
  }

  return getSyncWatcherState();
};

export const stopSyncWatcher = (): SyncWatcherState => {
  if (rescanTimer) {
    clearTimeout(rescanTimer);
    rescanTimer = null;
  }

  if (syncWatcher) {
    syncWatcher.close();
    syncWatcher = null;
  }

  watcherRoot = null;
  return getSyncWatcherState();
};

export const getSyncWatcherState = (): SyncWatcherState => ({
  running: Boolean(syncWatcher),
  root: watcherRoot,
  lastEventAt: lastWatcherEventAt
});

export const revealSyncFolder = async (targetPath?: string): Promise<void> => {
  const state = getSyncState();
  if (!state.syncRoot) {
    return;
  }

  const safeTarget = targetPath ? resolve(targetPath) : state.syncRoot;
  const safeRoot = resolve(state.syncRoot);

  if (safeTarget !== safeRoot && !safeTarget.startsWith(`${safeRoot}\\`)) {
    throw new Error('Folder is outside the Dropbox sync root.');
  }

  await shell.openPath(safeTarget);
};

const getDropboxPath = (): string | null => {
  const infoPathCandidates = [
    join(app.getPath('appData'), 'Dropbox', 'info.json'),
    join(process.env.LOCALAPPDATA ?? '', 'Dropbox', 'info.json'),
    join(app.getPath('userData'), '..', 'Dropbox', 'info.json')
  ];

  for (const infoPath of infoPathCandidates) {
    const pathFromInfo = readDropboxInfo(infoPath);
    if (pathFromInfo) {
      return pathFromInfo;
    }
  }

  const folderCandidates = [join(app.getPath('home'), 'Dropbox'), join(app.getPath('documents'), 'Dropbox')];
  return folderCandidates.find((candidate) => existsSync(candidate)) ?? null;
};

const readDropboxInfo = (infoPath: string): string | null => {
  if (!existsSync(infoPath)) {
    return null;
  }

  try {
    const info = JSON.parse(readFileSync(infoPath, 'utf8')) as {
      personal?: { path?: string };
      business?: { path?: string };
    };
    const candidate = info.business?.path ?? info.personal?.path;
    return candidate && existsSync(candidate) ? candidate : null;
  } catch {
    return null;
  }
};

const scanFolder = (folderPath: string): SyncFolderRecord => {
  const summary = scanRecursive(folderPath);
  const stat = safeStat(folderPath);

  return {
    name: basename(folderPath),
    path: folderPath,
    folderCount: summary.folderCount,
    fitsCount: summary.fitsCount,
    totalSizeBytes: summary.totalSizeBytes,
    updatedAt: stat?.mtime.toISOString() ?? null
  };
};

const collectFitsFiles = (syncRoot: string) => {
  const results: Array<{
    path: string;
    folderPath: string;
    fileName: string;
    extension: string;
    sizeBytes: number;
  }> = [];

  for (const entry of safeReadDir(syncRoot)) {
    if (!entry.isDirectory() || entry.name.startsWith('.')) {
      continue;
    }

    collectFitsFilesRecursive(join(syncRoot, entry.name), join(syncRoot, entry.name), results);
  }

  return results;
};

const collectFitsFilesRecursive = (
  rootFolderPath: string,
  folderPath: string,
  results: Array<{
    path: string;
    folderPath: string;
    fileName: string;
    extension: string;
    sizeBytes: number;
  }>
): void => {
  for (const entry of safeReadDir(folderPath)) {
    const entryPath = join(folderPath, entry.name);

    if (entry.isDirectory()) {
      collectFitsFilesRecursive(rootFolderPath, entryPath, results);
      continue;
    }

    if (!entry.isFile()) {
      continue;
    }

    const lowerName = entry.name.toLowerCase();
    const extension = [...fitsExtensions].find((item) => lowerName.endsWith(item));
    if (!extension) {
      continue;
    }

    results.push({
      path: entryPath,
      folderPath: rootFolderPath,
      fileName: entry.name,
      extension,
      sizeBytes: safeStat(entryPath)?.size ?? 0
    });
  }
};

const getIndexSummary = (): Pick<SyncState, 'indexedFitsCount' | 'stableFitsCount' | 'lastIndexedAt'> => {
  const row = getDatabase().prepare(
    `SELECT
       COUNT(*) AS indexed_count,
       SUM(CASE WHEN status = 'stable' THEN 1 ELSE 0 END) AS stable_count,
       MAX(updated_at) AS last_indexed_at
     FROM sync_files`
  ).get() as { indexed_count: number; stable_count: number | null; last_indexed_at: string | null };

  return {
    indexedFitsCount: row.indexed_count,
    stableFitsCount: row.stable_count ?? 0,
    lastIndexedAt: row.last_indexed_at
  };
};

const scanRecursive = (folderPath: string): { folderCount: number; fitsCount: number; totalSizeBytes: number } => {
  let folderCount = 0;
  let fitsCount = 0;
  let totalSizeBytes = 0;

  for (const entry of safeReadDir(folderPath)) {
    const entryPath = join(folderPath, entry.name);
    if (entry.isDirectory()) {
      folderCount += 1;
      const child = scanRecursive(entryPath);
      folderCount += child.folderCount;
      fitsCount += child.fitsCount;
      totalSizeBytes += child.totalSizeBytes;
      continue;
    }

    if (entry.isFile()) {
      const isFits = isFitsName(entry.name);
      if (isFits) {
        fitsCount += 1;
        totalSizeBytes += safeStat(entryPath)?.size ?? 0;
      }
    }
  }

  return { folderCount, fitsCount, totalSizeBytes };
};

const isFitsName = (name: string): boolean => {
  const lowerName = name.toLowerCase();
  return [...fitsExtensions].some((extension) => lowerName.endsWith(extension));
};

const safeReadDir = (folderPath: string) => {
  try {
    return readdirSync(folderPath, { withFileTypes: true });
  } catch {
    return [];
  }
};

const safeStat = (targetPath: string) => {
  try {
    return statSync(targetPath);
  } catch {
    return null;
  }
};
