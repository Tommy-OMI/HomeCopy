import { randomUUID } from 'node:crypto';
import { basename } from 'node:path';
import { getDatabase } from './database';

export type ProcessingJobRecord = {
  id: string;
  sourceFolderPath: string;
  sourceFolderName: string;
  fitsCount: number;
  totalSizeBytes: number;
  status: string;
  progress: number;
  currentStep: string;
  createdAt: string;
  updatedAt: string;
};

export const listProcessingJobs = (): ProcessingJobRecord[] => {
  const rows = getDatabase()
    .prepare(
      `SELECT
         id,
         source_folder_path,
         source_folder_name,
         fits_count,
         total_size_bytes,
         status,
         progress,
         current_step,
         created_at,
         updated_at
       FROM processing_jobs
       ORDER BY created_at DESC`
    )
    .all() as Array<Record<string, string | number>>;

  return rows.map(mapJobRow);
};

export const createProcessingJobFromIndex = (): ProcessingJobRecord => {
  const source = getDatabase()
    .prepare(
      `SELECT
         folder_path,
         COUNT(*) AS fits_count,
         COALESCE(SUM(size_bytes), 0) AS total_size_bytes
       FROM sync_files
       WHERE status IN ('stable', 'detected')
       GROUP BY folder_path
       ORDER BY fits_count DESC
       LIMIT 1`
    )
    .get() as { folder_path: string; fits_count: number; total_size_bytes: number } | undefined;

  if (!source) {
    throw new Error('No indexed FITS files are available for processing.');
  }

  const now = new Date().toISOString();
  const id = randomUUID();
  getDatabase()
    .prepare(
      `INSERT INTO processing_jobs (
         id, source_folder_path, source_folder_name, fits_count, total_size_bytes, status, progress, current_step, created_at, updated_at
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .run(id, source.folder_path, basename(source.folder_path), source.fits_count, source.total_size_bytes, 'queued', 0, 'Queued', now, now);

  getDatabase().prepare('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)').run('INFO', `Processing job queued from ${basename(source.folder_path)}`, now);
  return listProcessingJobs()[0];
};

const mapJobRow = (row: Record<string, string | number>): ProcessingJobRecord => ({
  id: String(row.id),
  sourceFolderPath: String(row.source_folder_path),
  sourceFolderName: String(row.source_folder_name),
  fitsCount: Number(row.fits_count),
  totalSizeBytes: Number(row.total_size_bytes),
  status: String(row.status),
  progress: Number(row.progress),
  currentStep: String(row.current_step),
  createdAt: String(row.created_at),
  updatedAt: String(row.updated_at)
});

