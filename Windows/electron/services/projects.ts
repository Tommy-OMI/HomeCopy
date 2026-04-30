import { dialog, shell } from 'electron';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { app } from 'electron';
import { getDatabase, getDatabasePath } from './database';
import type { CreateProjectInput, DashboardState, LogRecord, ProjectRecord, ProjectStats } from './types';

const filterFolders = ['L', 'R', 'G', 'B', 'Ha', 'OIII'];

export const getProjectsRoot = (): string => join(app.getPath('documents'), 'OMI Astera', 'Projects');

export const createProject = (input: CreateProjectInput): ProjectRecord => {
  const name = input.name.trim();
  if (!name) {
    throw new Error('Project name is required.');
  }

  const now = new Date().toISOString();
  const id = randomUUID();
  const slug = createSlug(name);
  const rootPath = uniqueProjectPath(slug);
  const projectFilePath = join(rootPath, 'project.omi.json');
  const objectType = input.objectType.trim() || 'Unknown';
  const filters = input.filters.length > 0 ? input.filters : filterFolders;
  const notes = input.notes?.trim() ?? '';

  createProjectFolders(rootPath);

  const project: ProjectRecord = {
    id,
    name,
    slug,
    objectType,
    filters,
    notes,
    rootPath,
    projectFilePath,
    status: 'Created',
    createdAt: now,
    updatedAt: now
  };

  writeProjectFile(project);
  insertProject(project);
  setSetting('current_project_id', id);
  addLog('INFO', `Project created: ${name}`);

  return project;
};

export const openProject = async (): Promise<ProjectRecord | null> => {
  const result = await dialog.showOpenDialog({
    title: 'Open OMI Astera Project',
    properties: ['openDirectory']
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const rootPath = result.filePaths[0];
  const projectFilePath = join(rootPath, 'project.omi.json');

  if (!existsSync(projectFilePath)) {
    addLog('WARNING', `Selected folder has no project.omi.json: ${rootPath}`);
    throw new Error('Selected folder is not an OMI Astera project.');
  }

  const project = JSON.parse(readFileSync(projectFilePath, 'utf8')) as ProjectRecord;
  insertProject({ ...project, rootPath, projectFilePath, updatedAt: new Date().toISOString() });
  setSetting('current_project_id', project.id);
  addLog('INFO', `Project opened: ${project.name}`);

  return project;
};

export const revealCurrentProject = async (): Promise<void> => {
  const state = getDashboardState();
  if (!state.currentProject) {
    return;
  }

  await shell.openPath(join(state.currentProject.rootPath, 'output'));
};

export const getDashboardState = (): DashboardState => {
  const projects = getProjects();
  const currentProjectId = getSetting('current_project_id');
  const currentProject = projects.find((project) => project.id === currentProjectId) ?? projects[0] ?? null;
  const stats = getCaptureStats();

  return {
    currentProject,
    projects,
    stats,
    logs: getLogs(),
    dbPath: getDatabasePath(),
    projectsRoot: getProjectsRoot()
  };
};

const createProjectFolders = (rootPath: string): void => {
  mkdirSync(rootPath, { recursive: true });
  filterFolders.forEach((filter) => mkdirSync(join(rootPath, 'raw', filter), { recursive: true }));
  ['calibration', 'output', 'logs'].forEach((folder) => mkdirSync(join(rootPath, folder), { recursive: true }));
};

const writeProjectFile = (project: ProjectRecord): void => {
  writeFileSync(project.projectFilePath, `${JSON.stringify(project, null, 2)}\n`, 'utf8');
};

const insertProject = (project: ProjectRecord): void => {
  const db = getDatabase();
  db.prepare(`
    INSERT INTO projects (
      id, name, slug, object_type, filters_json, notes, root_path, project_file_path, status, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      name = excluded.name,
      slug = excluded.slug,
      object_type = excluded.object_type,
      filters_json = excluded.filters_json,
      notes = excluded.notes,
      root_path = excluded.root_path,
      project_file_path = excluded.project_file_path,
      status = excluded.status,
      updated_at = excluded.updated_at
  `).run(
    project.id,
    project.name,
    project.slug,
    project.objectType,
    JSON.stringify(project.filters),
    project.notes,
    project.rootPath,
    project.projectFilePath,
    project.status,
    project.createdAt,
    project.updatedAt
  );
};

const getProjects = (): ProjectRecord[] => {
  const rows = getDatabase()
    .prepare(
      `SELECT id, name, slug, object_type, filters_json, notes, root_path, project_file_path, status, created_at, updated_at
       FROM projects
       ORDER BY updated_at DESC`
    )
    .all() as Array<Record<string, string>>;

  return rows.map((row) => ({
    id: row.id,
    name: row.name,
    slug: row.slug,
    objectType: row.object_type,
    filters: JSON.parse(row.filters_json) as string[],
    notes: row.notes,
    rootPath: row.root_path,
    projectFilePath: row.project_file_path,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  }));
};

const getProjectStats = (projectId: string): ProjectStats => {
  const row = getDatabase()
    .prepare(
      `SELECT COUNT(*) AS frame_count, COALESCE(SUM(size_bytes), 0) AS total_size_bytes
       FROM files
       WHERE project_id = ?`
    )
    .get(projectId) as { frame_count: number; total_size_bytes: number };

  return {
    lightFrames: row.frame_count,
    expectedFrames: 120,
    totalSizeBytes: row.total_size_bytes,
    stepsCompleted: 0,
    totalSteps: 7
  };
};

const getCaptureStats = (): ProjectStats => {
  const row = getDatabase()
    .prepare(
      `SELECT
         COUNT(*) AS frame_count,
         COALESCE(SUM(size_bytes), 0) AS total_size_bytes,
         SUM(CASE WHEN status = 'stable' THEN 1 ELSE 0 END) AS stable_count
       FROM sync_files`
    )
    .get() as { frame_count: number; total_size_bytes: number; stable_count: number | null };

  if (row.frame_count > 0) {
    return {
      lightFrames: row.frame_count,
      expectedFrames: 120,
      totalSizeBytes: row.total_size_bytes,
      stepsCompleted: row.stable_count && row.stable_count > 0 ? 1 : 0,
      totalSteps: 7
    };
  }

  const currentProjectId = getSetting('current_project_id');
  return currentProjectId ? getProjectStats(currentProjectId) : emptyStats();
};

const getLogs = (): LogRecord[] => {
  return getDatabase()
    .prepare('SELECT id, level, message, created_at FROM logs ORDER BY id DESC LIMIT 80')
    .all()
    .map((row) => {
      const item = row as { id: number; level: LogRecord['level']; message: string; created_at: string };
      return {
        id: item.id,
        level: item.level,
        message: item.message,
        createdAt: item.created_at
      };
    })
    .reverse();
};

const addLog = (level: LogRecord['level'], message: string): void => {
  getDatabase().prepare('INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)').run(level, message, new Date().toISOString());
};

const setSetting = (key: string, value: string): void => {
  getDatabase().prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value').run(key, value);
};

const getSetting = (key: string): string | null => {
  const row = getDatabase().prepare('SELECT value FROM settings WHERE key = ?').get(key) as { value: string } | undefined;
  return row?.value ?? null;
};

const createSlug = (value: string): string => {
  const ascii = value
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '_');

  return ascii || `Project_${new Date().toISOString().slice(0, 10)}`;
};

const uniqueProjectPath = (slug: string): string => {
  const projectsRoot = getProjectsRoot();
  mkdirSync(projectsRoot, { recursive: true });

  let attempt = 0;
  let target = join(projectsRoot, slug);

  while (existsSync(target)) {
    attempt += 1;
    target = join(projectsRoot, `${slug}_${attempt + 1}`);
  }

  return target;
};

const emptyStats = (): ProjectStats => ({
  lightFrames: 0,
  expectedFrames: 120,
  totalSizeBytes: 0,
  stepsCompleted: 0,
  totalSteps: 7
});
