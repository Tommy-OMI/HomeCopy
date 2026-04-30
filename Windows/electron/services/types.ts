export type ProjectRecord = {
  id: string;
  name: string;
  slug: string;
  objectType: string;
  filters: string[];
  notes: string;
  rootPath: string;
  projectFilePath: string;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type ProjectStats = {
  lightFrames: number;
  expectedFrames: number;
  totalSizeBytes: number;
  stepsCompleted: number;
  totalSteps: number;
};

export type LogRecord = {
  id: number;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  createdAt: string;
};

export type DashboardState = {
  currentProject: ProjectRecord | null;
  projects: ProjectRecord[];
  stats: ProjectStats;
  logs: LogRecord[];
  dbPath: string;
  projectsRoot: string;
};

export type CreateProjectInput = {
  name: string;
  objectType: string;
  filters: string[];
  notes?: string;
};

