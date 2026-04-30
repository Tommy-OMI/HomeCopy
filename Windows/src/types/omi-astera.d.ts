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

export type AuthUser = {
  memberId: string;
  contactId: string;
  email: string;
  name: string;
  photoUrl: string;
  loggedInAt: string;
};

export type AuthState = {
  isLoggedIn: boolean;
  user: AuthUser | null;
  hasRefreshToken: boolean;
  expiresAt: string;
  callbackScheme: string;
  lastError: string;
  lastStep: string;
};

export type LicenseState = {
  isActive: boolean;
  licenseKey: string;
  accountId: string;
  plan: string;
  validUntil: string;
  dropboxSharedLink: string;
  associatedLocalPath: string;
  activatedAt: string;
};

export type StartupCheck = {
  id: string;
  label: string;
  status: 'passed' | 'failed' | 'placeholder';
  detail: string;
};

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

declare global {
  interface Window {
    omiAstera?: {
      appName: string;
      platform: NodeJS.Platform;
      getAuthState: () => Promise<AuthState>;
      login: () => Promise<AuthState>;
      logout: () => Promise<AuthState>;
      getLicenseState: () => Promise<LicenseState>;
      activateLicense: (input: { licenseKey: string }) => Promise<LicenseState>;
      chooseDropboxAssociation: () => Promise<LicenseState>;
      confirmDetectedDropboxAssociation: () => Promise<LicenseState>;
      getStartupChecks: () => Promise<StartupCheck[]>;
      getDashboardState: () => Promise<DashboardState>;
      createProject: (input: CreateProjectInput) => Promise<ProjectRecord>;
      openProject: () => Promise<ProjectRecord | null>;
      revealCurrentProject: () => Promise<void>;
      listProcessingJobs: () => Promise<ProcessingJobRecord[]>;
      createProcessingJobFromIndex: () => Promise<ProcessingJobRecord>;
      getSyncState: () => Promise<SyncState>;
      rescanSyncFiles: () => Promise<SyncState>;
      revealSyncFolder: (targetPath?: string) => Promise<void>;
    };
  }
}
