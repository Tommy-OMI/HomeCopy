import {
  Bell,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  Database,
  Edit3,
  ExternalLink,
  FileArchive,
  FolderOpen,
  HardDrive,
  KeyRound,
  LogOut,
  UserCircle,
  RefreshCcw,
  Settings,
  Sparkles,
  Star,
  X,
  UserRound
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  navItems,
  pipelineSteps,
  plannerTargets,
  quickActions,
  statusCards,
  storage,
  systemStatus
} from './data/dashboard';
import type {
  CreateProjectInput,
  AuthState,
  DashboardState,
  LicenseState,
  LogRecord,
  ProcessingJobRecord,
  ProjectRecord,
  ProjectStats,
  StartupCheck,
  SyncState
} from './types/omi-astera';

type ViewName = 'Dashboard' | 'AI Planner' | 'Processing' | 'Files & Syncing' | 'Settings';

const emptyStats: ProjectStats = {
  lightFrames: 0,
  expectedFrames: 120,
  totalSizeBytes: 0,
  stepsCompleted: 0,
  totalSteps: 7
};

const emptyDashboardState: DashboardState = {
  currentProject: null,
  projects: [],
  stats: emptyStats,
  logs: [],
  dbPath: '',
  projectsRoot: ''
};

const emptySyncState: SyncState = {
  syncRoot: null,
  source: 'Dropbox folder not detected',
  folders: [],
  indexedFitsCount: 0,
  stableFitsCount: 0,
  lastIndexedAt: null
};

const emptyAuthState: AuthState = {
  isLoggedIn: false,
  user: null,
  hasRefreshToken: false,
  expiresAt: '',
  callbackScheme: 'omiastro://auth',
  lastError: '',
  lastStep: ''
};

const emptyLicenseState: LicenseState = {
  isActive: false,
  licenseKey: '',
  accountId: '',
  plan: '',
  validUntil: '',
  dropboxSharedLink: '',
  associatedLocalPath: '',
  activatedAt: ''
};

const defaultProjectInput: CreateProjectInput = {
  name: 'M31 - Andromeda Galaxy',
  objectType: 'Galaxy',
  filters: ['L', 'R', 'G', 'B', 'Ha', 'OIII'],
  notes: ''
};

const AppShellHeader = ({
  activeView,
  auth,
  onLogin,
  onLogout,
  onOpenSettings
}: {
  activeView: ViewName;
  auth: AuthState;
  onLogin: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
}) => (
  <header className="app-header">
    <h1>{activeView}</h1>
    <div className="header-actions">
      <span className="service-state">
        <span />
        Service Online
      </span>
      <button className="icon-button" aria-label="Notifications">
        <Bell size={20} />
        <strong>3</strong>
      </button>
      <button className="icon-button" aria-label="Settings">
        <Settings size={20} />
      </button>
      <div className="account-menu">
      <button className="account-button" onClick={auth.isLoggedIn ? undefined : onLogin}>
        <span className="avatar">
          {auth.user?.photoUrl ? <img src={auth.user.photoUrl} alt="" /> : <UserRound size={20} />}
        </span>
        <span>
          <strong>{auth.isLoggedIn ? auth.user?.name || auth.user?.email || 'OMI Member' : 'Guest'}</strong>
          <small>{auth.isLoggedIn ? auth.user?.email || 'Logged in' : 'Click to log in'}</small>
        </span>
        {auth.isLoggedIn ? (
          <ChevronDown size={18} />
        ) : (
          <ChevronDown size={18} />
        )}
      </button>
      {auth.isLoggedIn ? (
        <div className="account-dropdown">
          <button>
            <UserCircle size={17} />
            Profile
          </button>
          <button onClick={onOpenSettings}>
            <Settings size={17} />
            Settings
          </button>
          <button onClick={onLogout}>
            <LogOut size={17} />
            Logout
          </button>
        </div>
      ) : null}
      </div>
    </div>
  </header>
);

const Sidebar = ({ activeView, onSelectView }: { activeView: ViewName; onSelectView: (view: ViewName) => void }) => (
  <aside className="sidebar">
    <div className="brand">
      <div className="brand-mark">
        <Sparkles size={24} />
      </div>
      <div>
        <strong>OMI Astera</strong>
        <span>Astro Desktop Control Platform</span>
      </div>
    </div>

    <nav className="nav-list" aria-label="Primary">
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <button
            className={item.label === activeView ? 'nav-item active' : 'nav-item'}
            key={item.label}
            onClick={() => onSelectView(item.label as ViewName)}
          >
            <Icon size={22} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>

    <div className="system-panel">
      <span className="panel-label">System Status</span>
      {systemStatus.map(([label, value]) => (
        <div className="status-row" key={label}>
          <span>
            <Circle size={9} />
            {label}
          </span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>

    <div className="sidebar-footer">
      <span>v0.9.0</span>
      <strong>OMI ASTRO</strong>
      <small>Explore. Capture. Inspire.</small>
    </div>
  </aside>
);

const StatusCards = () => (
  <section className="status-grid" aria-label="Service status">
    {statusCards.map((card) => {
      const Icon = card.icon;
      return (
        <article className="metric-card" key={card.label}>
          <div className={`metric-icon ${card.tone}`}>
            <Icon size={27} />
          </div>
          <div>
            <span className="metric-label">{card.label}</span>
            <strong className={`metric-title ${card.tone}`}>{card.title}</strong>
            <span>{card.value}</span>
            {card.meta.map((item) => (
              <small key={item}>{item}</small>
            ))}
          </div>
        </article>
      );
    })}
    <article className="metric-card storage-card">
      <div className="metric-icon violet">
        <Database size={28} />
      </div>
      <div className="storage-content">
        <span className="metric-label">Storage</span>
        <strong>
          <span>{storage.usedPercent}%</span> Used
        </strong>
        <small>
          {storage.used} / {storage.total}
        </small>
        <div className="storage-bar">
          <span style={{ width: `${storage.usedPercent}%` }} />
        </div>
      </div>
    </article>
  </section>
);

const ProjectPanel = ({ project, stats, projectsRoot }: { project: ProjectRecord | null; stats: ProjectStats; projectsRoot: string }) => {
  const projectStats = [
    { label: 'Light Frames', value: `${stats.lightFrames} / ${stats.expectedFrames}`, meta: 'Frames' },
    { label: 'Total Size', value: formatBytes(stats.totalSizeBytes), meta: '' },
    { label: 'Steps Completed', value: `${stats.stepsCompleted} / ${stats.totalSteps}`, meta: '' },
    { label: 'Elapsed Time', value: '00:00:00', meta: 'HH:MM:SS' },
    { label: 'Est. Remaining', value: '--:--:--', meta: 'HH:MM:SS' }
  ];

  return (
  <section className="panel current-project">
    <div className="section-title">Current Project</div>
    {project ? (
      <div className="project-main">
      <div className="astro-preview" aria-label="Galaxy project preview">
        <span className="galaxy-core" />
        <span className="galaxy-arm one" />
        <span className="galaxy-arm two" />
      </div>
      <div className="project-details">
        <h2>
          {project.name}
          <button className="inline-icon" aria-label="Edit project">
            <Edit3 size={17} />
          </button>
        </h2>
        <dl>
          <div>
            <dt>Project Path</dt>
            <dd>{project.rootPath}</dd>
          </div>
          <div>
            <dt>Started</dt>
            <dd>{formatDateTime(project.createdAt)}</dd>
          </div>
          <div>
            <dt>Object Type</dt>
            <dd>{project.objectType}</dd>
          </div>
          <div>
            <dt>Filters</dt>
            <dd>{project.filters.join(', ')}</dd>
          </div>
          <div>
            <dt>Notes</dt>
            <dd>{project.notes || '--'}</dd>
          </div>
        </dl>
      </div>
      <div className="progress-ring" aria-label="68 percent complete">
        <span>{Math.round((stats.stepsCompleted / stats.totalSteps) * 100)}%</span>
        <small>{project.status}</small>
      </div>
      </div>
    ) : (
      <div className="empty-project">
        <h2>No Local Project Yet</h2>
        <p>Projects will be created under {projectsRoot || 'Documents/OMI Astera/Projects'} with raw, calibration, output, logs, and project metadata folders.</p>
      </div>
    )}

    <div className="project-stats">
      {projectStats.map((stat) => (
        <article className="stat-tile" key={stat.label}>
          <span>{stat.label}</span>
          <strong>{stat.value}</strong>
          {stat.meta ? <small>{stat.meta}</small> : <small>&nbsp;</small>}
        </article>
      ))}
    </div>
  </section>
  );
};

const PipelinePanel = () => (
  <section className="panel pipeline-panel">
    <div className="section-title">Processing Pipeline</div>
    <div className="pipeline">
      {pipelineSteps.map((step, index) => (
        <div className={`pipeline-step ${step.status}`} key={step.label}>
          <span className="pipeline-dot">{step.status === 'pending' ? <Circle size={15} /> : <Check size={15} />}</span>
          {index < pipelineSteps.length - 1 && <span className="pipeline-line" />}
          <strong>{step.label}</strong>
        </div>
      ))}
    </div>
  </section>
);

const LogConsole = ({ items }: { items: LogRecord[] }) => (
  <section className="panel log-panel">
    <div className="panel-header">
      <div className="section-title">Log Console</div>
      <div className="filter-group">
        <button className="chip active">All</button>
        <button className="chip">Info</button>
        <button className="chip warning">Warning</button>
        <button className="chip error">Error</button>
      </div>
    </div>
    <div className="log-list">
      {items.length === 0 ? (
        <div className="log-empty">No local agent events yet.</div>
      ) : (
        items.map((item) => (
        <div className="log-row" key={item.id}>
          <time>{formatLogTime(item.createdAt)}</time>
          <strong className={item.level.toLowerCase()}>{item.level}</strong>
          <span>{item.message}</span>
        </div>
        ))
      )}
    </div>
  </section>
);

const ProjectDialog = ({
  open,
  creating,
  error,
  onClose,
  onCreate
}: {
  open: boolean;
  creating: boolean;
  error: string;
  onClose: () => void;
  onCreate: (input: CreateProjectInput) => void;
}) => {
  const [name, setName] = useState(defaultProjectInput.name);
  const [objectType, setObjectType] = useState(defaultProjectInput.objectType);
  const [filters, setFilters] = useState(defaultProjectInput.filters.join(', '));
  const [notes, setNotes] = useState(defaultProjectInput.notes ?? '');

  useEffect(() => {
    if (open) {
      setName(defaultProjectInput.name);
      setObjectType(defaultProjectInput.objectType);
      setFilters(defaultProjectInput.filters.join(', '));
      setNotes('');
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <form
        className="project-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          onCreate({
            name,
            objectType,
            filters: filters
              .split(',')
              .map((filter) => filter.trim())
              .filter(Boolean),
            notes
          });
        }}
      >
        <div className="dialog-header">
          <div>
            <span className="section-title">New Project</span>
            <h2>Create Local Astera Project</h2>
          </div>
          <button type="button" className="icon-button" aria-label="Close dialog" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <label>
          Project Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Object Type
          <input value={objectType} onChange={(event) => setObjectType(event.target.value)} />
        </label>
        <label>
          Filters
          <input value={filters} onChange={(event) => setFilters(event.target.value)} />
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
        </label>
        {error ? <div className="dialog-error">{error}</div> : null}
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="primary-button" disabled={creating}>
            {creating ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  );
};

const PlannerPanel = () => (
  <section className="panel planner-panel">
    <div className="panel-header">
      <div>
        <div className="section-title accent">AI Planner</div>
        <h2>Best Targets Tonight</h2>
      </div>
      <button className="secondary-button">Refresh</button>
    </div>
    <div className="planner-meta">
      <span>
        <CalendarDays size={15} />
        2024-12-20
      </span>
      <span>Location: Qinghai, China (Bortle 2)</span>
      <span>Weather: Clear</span>
      <span>Seeing: 1.4"</span>
    </div>
    <div className="target-list">
      {plannerTargets.map((target) => (
        <article className={target.rank === 1 ? 'target-card selected' : 'target-card'} key={target.name}>
          <div className={`target-image ${target.tone}`}>
            <strong>{target.rank}</strong>
            <Star size={24} />
          </div>
          <div className="target-copy">
            <h3>{target.name}</h3>
            <p>
              Altitude: {target.altitude} <span>Visibility: {target.visibility}</span> <span>Moon Impact: {target.moon}</span>
            </p>
            <p>Recommended Filters: {target.filters}</p>
            <p>Recommended Exposure: {target.exposure}</p>
          </div>
          <strong className="score">{target.score}</strong>
        </article>
      ))}
    </div>
    <button className="primary-button">
      View Full Planner
      <ChevronRight size={18} />
    </button>
  </section>
);

const QuickActions = ({ onNewProject, onOpenProject, onRevealProject }: { onNewProject: () => void; onOpenProject: () => void; onRevealProject: () => void }) => (
  <section className="panel actions-panel">
    <div className="section-title">Quick Actions</div>
    <div className="action-grid">
      {quickActions.map((action) => {
        const Icon = action.icon;
        return (
          <button
            className="action-button"
            key={action.label}
            onClick={() => {
              if (action.label === 'New Project') onNewProject();
              if (action.label === 'Open Project') onOpenProject();
              if (action.label === 'Open Output Folder') onRevealProject();
            }}
          >
            <Icon size={34} />
            <span>{action.label}</span>
          </button>
        );
      })}
    </div>
  </section>
);

const Dashboard = ({
  state,
  activeView,
  auth,
  onNewProject,
  onOpenProject,
  onRevealProject,
  onLogin,
  onLogout,
  onOpenSettings
}: {
  state: DashboardState;
  activeView: ViewName;
  auth: AuthState;
  onNewProject: () => void;
  onOpenProject: () => void;
  onRevealProject: () => void;
  onLogin: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
}) => (
  <main className="dashboard">
    <AppShellHeader activeView={activeView} auth={auth} onLogin={onLogin} onLogout={onLogout} onOpenSettings={onOpenSettings} />
    <StatusCards />
    <div className="dashboard-grid">
      <div className="main-column">
        <ProjectPanel project={state.currentProject} stats={state.stats} projectsRoot={state.projectsRoot} />
        <PipelinePanel />
        <LogConsole items={state.logs} />
      </div>
      <div className="side-column">
        <PlannerPanel />
        <QuickActions onNewProject={onNewProject} onOpenProject={onOpenProject} onRevealProject={onRevealProject} />
      </div>
    </div>
  </main>
);

const FilesSyncingPage = ({
  activeView,
  auth,
  syncState,
  onRefresh,
  onRevealFolder,
  onLogin,
  onLogout,
  onOpenSettings
}: {
  activeView: ViewName;
  auth: AuthState;
  syncState: SyncState;
  onRefresh: () => void;
  onRevealFolder: (targetPath?: string) => void;
  onLogin: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
}) => {
  const totalFits = syncState.folders.reduce((total, folder) => total + folder.fitsCount, 0);
  const totalSize = syncState.folders.reduce((total, folder) => total + folder.totalSizeBytes, 0);

  return (
    <main className="dashboard">
      <AppShellHeader activeView={activeView} auth={auth} onLogin={onLogin} onLogout={onLogout} onOpenSettings={onOpenSettings} />
      <section className="files-page">
        <div className="panel sync-root-panel">
          <div>
            <span className="section-title">Dropbox Local Sync Directory</span>
            <h2>{syncState.syncRoot ?? 'Not Detected'}</h2>
            <p>{syncState.source}</p>
          </div>
          <div className="sync-actions">
            <button className="secondary-button" onClick={onRefresh}>
              <RefreshCcw size={16} />
              Rescan Index
            </button>
            <button className="primary-button" disabled={!syncState.syncRoot} onClick={() => onRevealFolder()}>
              <FolderOpen size={17} />
              Open Folder
            </button>
          </div>
        </div>

        <div className="sync-summary-grid">
          <article className="stat-tile">
            <span>Folders</span>
            <strong>{syncState.folders.length}</strong>
            <small>Under sync root</small>
          </article>
          <article className="stat-tile">
            <span>FITS Files</span>
            <strong>{totalFits}</strong>
            <small>.fit / .fits</small>
          </article>
          <article className="stat-tile">
            <span>Indexed</span>
            <strong>{syncState.indexedFitsCount}</strong>
            <small>{syncState.stableFitsCount} stable</small>
          </article>
          <article className="stat-tile">
            <span>FITS Size</span>
            <strong>{formatBytes(totalSize)}</strong>
            <small>{syncState.lastIndexedAt ? `Last indexed ${formatDateTime(syncState.lastIndexedAt)}` : 'Not indexed yet'}</small>
          </article>
        </div>

        <section className="panel folder-list-panel">
          <div className="panel-header">
            <div>
              <span className="section-title">Capture Folders</span>
              <h2>Folders Created by NINA and Other Capture Tools</h2>
            </div>
          </div>
          <div className="folder-table">
            {syncState.folders.length === 0 ? (
              <div className="folder-empty">
                <HardDrive size={34} />
                <span>No folders found in the current Dropbox sync directory.</span>
              </div>
            ) : (
              syncState.folders.map((folder) => (
                <button className="folder-row" key={folder.path} onClick={() => onRevealFolder(folder.path)}>
                  <span className="folder-name">
                    <FolderOpen size={21} />
                    <strong>{folder.name}</strong>
                    <small>{folder.path}</small>
                  </span>
                  <span>
                    <FileArchive size={18} />
                    {folder.fitsCount} FITS
                  </span>
                  <span>{folder.folderCount} folders</span>
                  <span>{formatBytes(folder.totalSizeBytes)}</span>
                  <span>{folder.updatedAt ? formatDateTime(folder.updatedAt) : '--'}</span>
                </button>
              ))
            )}
          </div>
        </section>
      </section>
    </main>
  );
};

const SettingsPage = ({
  activeView,
  auth,
  license,
  checks,
  licenseInput,
  activating,
  error,
  onLicenseInput,
  onActivate,
  onConfirmDetectedDropbox,
  onChooseDropboxFolder,
  onLogin,
  onLogout,
  onOpenSettings
}: {
  activeView: ViewName;
  auth: AuthState;
  license: LicenseState;
  checks: StartupCheck[];
  licenseInput: string;
  activating: boolean;
  error: string;
  onLicenseInput: (value: string) => void;
  onActivate: () => void;
  onConfirmDetectedDropbox: () => void;
  onChooseDropboxFolder: () => void;
  onLogin: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
}) => (
  <main className="dashboard">
    <AppShellHeader activeView={activeView} auth={auth} onLogin={onLogin} onLogout={onLogout} onOpenSettings={onOpenSettings} />
    <section className="settings-page">
      <div className="panel settings-panel">
        <div>
          <span className="section-title">Account</span>
          <h2>{auth.isLoggedIn ? auth.user?.email || auth.user?.name : 'Guest'}</h2>
          <p>{auth.isLoggedIn ? 'Signed in with Wix Headless OAuth + PKCE.' : 'Log in with Wix hosted authentication before activating a license.'}</p>
          {auth.lastStep ? <small className="auth-diagnostic">Last auth step: {auth.lastStep}</small> : null}
          {auth.lastError ? <small className="auth-diagnostic error">Last auth error: {auth.lastError}</small> : null}
        </div>
        <button className={auth.isLoggedIn ? 'secondary-button' : 'primary-button'} onClick={auth.isLoggedIn ? onLogout : onLogin}>
          {auth.isLoggedIn ? 'Log Out' : 'Log In'}
        </button>
      </div>

      <div className="panel settings-panel license-panel">
        <div>
          <span className="section-title">License</span>
          <h2>{license.isActive ? `${license.plan || 'Active License'}` : 'Activate License'}</h2>
          <p>License activation calls the Wix HTTP API and stores the returned Dropbox shared link locally.</p>
        </div>
        <div className="license-form">
          <label>
            License Key
            <input value={licenseInput} onChange={(event) => onLicenseInput(event.target.value)} placeholder="Enter license key from omiastro.com" />
          </label>
          <button className="primary-button" disabled={!auth.isLoggedIn || activating} onClick={onActivate}>
            <KeyRound size={17} />
            {activating ? 'Activating...' : 'Activate'}
          </button>
        </div>
        {error ? <div className="dialog-error">{error}</div> : null}
        {license.isActive ? (
          <div className="license-details">
            <span>Account: {license.accountId || '--'}</span>
            <span>Member ID: {auth.user?.memberId || '--'}</span>
            <span>Valid Until: {license.validUntil || '--'}</span>
            <span>Dropbox Shared Link: {license.dropboxSharedLink || '--'}</span>
            <span>Associated Local Path: {license.associatedLocalPath || '--'}</span>
          </div>
        ) : null}
        <div className="association-actions">
          <button className="secondary-button" disabled={!license.isActive} onClick={onConfirmDetectedDropbox}>
            Confirm Detected Dropbox
          </button>
          <button className="secondary-button" disabled={!license.isActive} onClick={onChooseDropboxFolder}>
            Choose Local Folder
          </button>
        </div>
      </div>

      <div className="panel checks-panel">
        <span className="section-title">Startup Checks</span>
        <div className="check-list">
          {checks.map((check) => (
            <article className={`check-row ${check.status}`} key={check.id}>
              <CheckCircle2 size={19} />
              <div>
                <strong>{check.label}</strong>
                <span>{check.detail}</span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  </main>
);

const ProcessingPage = ({
  activeView,
  auth,
  jobs,
  error,
  onCreateJob,
  onLogin,
  onLogout,
  onOpenSettings
}: {
  activeView: ViewName;
  auth: AuthState;
  jobs: ProcessingJobRecord[];
  error: string;
  onCreateJob: () => void;
  onLogin: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
}) => (
  <main className="dashboard">
    <AppShellHeader activeView={activeView} auth={auth} onLogin={onLogin} onLogout={onLogout} onOpenSettings={onOpenSettings} />
    <section className="processing-page">
      <div className="panel processing-header-panel">
        <div>
          <span className="section-title">Processing Queue</span>
          <h2>Local Job Staging</h2>
          <p>Jobs are staged locally first. The next slice will submit these jobs to Wix API and the Processing Server.</p>
        </div>
        <button className="primary-button" onClick={onCreateJob}>
          Create Job From FITS Index
        </button>
      </div>
      {error ? <div className="dialog-error">{error}</div> : null}
      <div className="processing-job-list">
        {jobs.length === 0 ? (
          <section className="panel placeholder-page">
            <span className="section-title">No Jobs</span>
            <h2>Run a FITS rescan, then create a processing job from the indexed files.</h2>
          </section>
        ) : (
          jobs.map((job) => (
            <article className="panel processing-job-card" key={job.id}>
              <div>
                <span className="section-title">{job.status}</span>
                <h2>{job.sourceFolderName}</h2>
                <p>{job.sourceFolderPath}</p>
              </div>
              <div className="job-metrics">
                <span>{job.fitsCount} FITS</span>
                <span>{formatBytes(job.totalSizeBytes)}</span>
                <span>{job.currentStep}</span>
                <span>{job.progress}%</span>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  </main>
);

const PlaceholderPage = ({
  activeView,
  auth,
  onLogin,
  onLogout,
  onOpenSettings
}: {
  activeView: ViewName;
  auth: AuthState;
  onLogin: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
}) => (
  <main className="dashboard">
    <AppShellHeader activeView={activeView} auth={auth} onLogin={onLogin} onLogout={onLogout} onOpenSettings={onOpenSettings} />
    <section className="panel placeholder-page">
      <span className="section-title">{activeView}</span>
      <h2>{activeView} module is reserved for the next implementation slice.</h2>
    </section>
  </main>
);

export const App = () => {
  const [state, setState] = useState<DashboardState>(emptyDashboardState);
  const [syncState, setSyncState] = useState<SyncState>(emptySyncState);
  const [auth, setAuth] = useState<AuthState>(emptyAuthState);
  const [license, setLicense] = useState<LicenseState>(emptyLicenseState);
  const [startupChecks, setStartupChecks] = useState<StartupCheck[]>([]);
  const [processingJobs, setProcessingJobs] = useState<ProcessingJobRecord[]>([]);
  const [licenseInput, setLicenseInput] = useState('');
  const [activating, setActivating] = useState(false);
  const [activeView, setActiveView] = useState<ViewName>('Dashboard');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const refresh = async () => {
    if (!window.omiAstera) {
      setState({ ...emptyDashboardState, projectsRoot: 'Documents/OMI Astera/Projects' });
      setAuth(emptyAuthState);
      setLicense(emptyLicenseState);
      return;
    }

    const [dashboardState, authState, licenseState, checks] = await Promise.all([
      window.omiAstera.getDashboardState(),
      window.omiAstera.getAuthState(),
      window.omiAstera.getLicenseState(),
      window.omiAstera.getStartupChecks()
    ]);
    setState(dashboardState);
    setAuth(authState);
    setLicense(licenseState);
    setStartupChecks(checks);
    setLicenseInput(licenseState.licenseKey);
  };

  const refreshProcessingJobs = async () => {
    if (!window.omiAstera) {
      setProcessingJobs([]);
      return;
    }

    setProcessingJobs(await window.omiAstera.listProcessingJobs());
  };

  const refreshSyncState = async () => {
    if (!window.omiAstera) {
      setSyncState(emptySyncState);
      return;
    }

    setSyncState(await window.omiAstera.getSyncState());
  };

  const rescanSyncFiles = async () => {
    if (!window.omiAstera) {
      setSyncState(emptySyncState);
      return;
    }

    setSyncState(await window.omiAstera.rescanSyncFiles());
    await refresh();
  };

  useEffect(() => {
    refresh().catch((unknownError) => setError(getErrorMessage(unknownError)));
  }, []);

  useEffect(() => {
    if (activeView === 'Files & Syncing') {
      refreshSyncState().catch((unknownError) => setError(getErrorMessage(unknownError)));
    }

    if (activeView === 'Processing') {
      refreshProcessingJobs().catch((unknownError) => setError(getErrorMessage(unknownError)));
    }
  }, [activeView]);

  const createProject = async (input: CreateProjectInput) => {
    setCreating(true);
    setError('');
    try {
      if (!window.omiAstera) {
        throw new Error('Project creation is available in the Electron desktop app.');
      }
      await window.omiAstera.createProject(input);
      await refresh();
      setDialogOpen(false);
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
    } finally {
      setCreating(false);
    }
  };

  const openProject = async () => {
    setError('');
    try {
      if (!window.omiAstera) {
        throw new Error('Open Project is available in the Electron desktop app.');
      }
      await window.omiAstera.openProject();
      await refresh();
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
    }
  };

  const revealProject = async () => {
    await window.omiAstera?.revealCurrentProject();
  };

  const revealSyncFolder = async (targetPath?: string) => {
    await window.omiAstera?.revealSyncFolder(targetPath);
  };

  const login = async () => {
    if (!window.omiAstera) return;
    setError('');
    try {
      setAuth(await window.omiAstera.login());
      await refresh();
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
      await refresh();
    }
  };

  const logout = async () => {
    if (!window.omiAstera) return;
    setAuth(await window.omiAstera.logout());
    await refresh();
  };

  const activateLicense = async () => {
    if (!window.omiAstera) return;
    setActivating(true);
    setError('');
    try {
      setLicense(await window.omiAstera.activateLicense({ licenseKey: licenseInput }));
      setStartupChecks(await window.omiAstera.getStartupChecks());
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
    } finally {
      setActivating(false);
    }
  };

  const createProcessingJob = async () => {
    if (!window.omiAstera) return;
    setError('');
    try {
      await window.omiAstera.createProcessingJobFromIndex();
      await refreshProcessingJobs();
      await refresh();
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
    }
  };

  const refreshLicenseChecks = async (nextLicense: LicenseState) => {
    setLicense(nextLicense);
    setStartupChecks(await window.omiAstera!.getStartupChecks());
  };

  const confirmDetectedDropbox = async () => {
    if (!window.omiAstera) return;
    setError('');
    try {
      await refreshLicenseChecks(await window.omiAstera.confirmDetectedDropboxAssociation());
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
    }
  };

  const chooseDropboxFolder = async () => {
    if (!window.omiAstera) return;
    setError('');
    try {
      await refreshLicenseChecks(await window.omiAstera.chooseDropboxAssociation());
    } catch (unknownError) {
      setError(getErrorMessage(unknownError));
    }
  };

  const appTitle = useMemo(() => state.currentProject?.name ?? 'OMI Astera', [state.currentProject]);
  const mainContent =
    activeView === 'Dashboard' ? (
      <Dashboard
        state={state}
        activeView={activeView}
        auth={auth}
        onNewProject={() => setDialogOpen(true)}
        onOpenProject={openProject}
        onRevealProject={revealProject}
        onLogin={login}
        onLogout={logout}
        onOpenSettings={() => setActiveView('Settings')}
      />
    ) : activeView === 'Files & Syncing' ? (
      <FilesSyncingPage
        activeView={activeView}
        auth={auth}
        syncState={syncState}
        onRefresh={rescanSyncFiles}
        onRevealFolder={revealSyncFolder}
        onLogin={login}
        onLogout={logout}
        onOpenSettings={() => setActiveView('Settings')}
      />
    ) : activeView === 'Settings' ? (
      <SettingsPage
        activeView={activeView}
        auth={auth}
        license={license}
        checks={startupChecks}
        licenseInput={licenseInput}
        activating={activating}
        error={error}
        onLicenseInput={setLicenseInput}
        onActivate={activateLicense}
        onConfirmDetectedDropbox={confirmDetectedDropbox}
        onChooseDropboxFolder={chooseDropboxFolder}
        onLogin={login}
        onLogout={logout}
        onOpenSettings={() => setActiveView('Settings')}
      />
    ) : activeView === 'Processing' ? (
      <ProcessingPage
        activeView={activeView}
        auth={auth}
        jobs={processingJobs}
        error={error}
        onCreateJob={createProcessingJob}
        onLogin={login}
        onLogout={logout}
        onOpenSettings={() => setActiveView('Settings')}
      />
    ) : (
      <PlaceholderPage activeView={activeView} auth={auth} onLogin={login} onLogout={logout} onOpenSettings={() => setActiveView('Settings')} />
    );

  return (
    <div className="app-frame" aria-label={appTitle}>
      <Sidebar activeView={activeView} onSelectView={setActiveView} />
      {mainContent}
      <ProjectDialog open={dialogOpen} creating={creating} error={error} onClose={() => setDialogOpen(false)} onCreate={createProject} />
      {error ? <div className="toast-error">{error}</div> : null}
      <a className="site-link" href="https://omiastro.com" target="_blank" rel="noreferrer">
        <ExternalLink size={15} />
        omiastro.com
      </a>
    </div>
  );
};

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatDateTime = (value: string): string => {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value));
};

const formatLogTime = (value: string): string => {
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(new Date(value));
};

const getErrorMessage = (error: unknown): string => {
  return error instanceof Error ? error.message : String(error);
};
