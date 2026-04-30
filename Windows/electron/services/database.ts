import { app } from 'electron';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';

let database: DatabaseSync | null = null;
let databasePath = '';

export const getDatabasePath = (): string => databasePath;

export const getDatabase = (): DatabaseSync => {
  if (database) {
    return database;
  }

  const dataDir = join(app.getPath('userData'), 'data');
  mkdirSync(dataDir, { recursive: true });
  databasePath = join(dataDir, 'omi-astera.sqlite');
  database = new DatabaseSync(databasePath);
  database.exec('PRAGMA foreign_keys = ON;');
  migrate(database);

  return database;
};

const migrate = (db: DatabaseSync): void => {
  db.exec(`
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS license_cache (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS projects (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      slug TEXT NOT NULL,
      object_type TEXT NOT NULL,
      filters_json TEXT NOT NULL,
      notes TEXT NOT NULL DEFAULT '',
      root_path TEXT NOT NULL,
      project_file_path TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS files (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      path TEXT NOT NULL,
      filter TEXT,
      size_bytes INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      detected_at TEXT NOT NULL,
      stable_at TEXT,
      synced_at TEXT,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sync_files (
      path TEXT PRIMARY KEY,
      folder_path TEXT NOT NULL,
      folder_name TEXT NOT NULL,
      file_name TEXT NOT NULL,
      extension TEXT NOT NULL,
      size_bytes INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      detected_at TEXT NOT NULL,
      stable_at TEXT,
      synced_at TEXT,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL,
      status TEXT NOT NULL,
      progress INTEGER NOT NULL DEFAULT 0,
      current_step TEXT NOT NULL DEFAULT 'Not Started',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS processing_jobs (
      id TEXT PRIMARY KEY,
      source_folder_path TEXT NOT NULL,
      source_folder_name TEXT NOT NULL,
      fits_count INTEGER NOT NULL DEFAULT 0,
      total_size_bytes INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      progress INTEGER NOT NULL DEFAULT 0,
      current_step TEXT NOT NULL DEFAULT 'Queued',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      level TEXT NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_files_project_id ON files(project_id);
    CREATE INDEX IF NOT EXISTS idx_sync_files_folder_path ON sync_files(folder_path);
    CREATE INDEX IF NOT EXISTS idx_sync_files_status ON sync_files(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_project_id ON jobs(project_id);
    CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);
  `);
};
