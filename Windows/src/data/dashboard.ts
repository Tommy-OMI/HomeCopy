import type { LucideIcon } from 'lucide-react';
import {
  Brain,
  Cloud,
  Database,
  Folder,
  Gauge,
  HardDrive,
  Home,
  ListChecks,
  Monitor,
  Plus,
  RefreshCcw,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  UploadCloud
} from 'lucide-react';

export type NavItem = {
  label: string;
  icon: LucideIcon;
};

export type StatusCard = {
  label: string;
  title: string;
  value: string;
  meta: string[];
  tone: 'green' | 'blue' | 'violet' | 'amber';
  icon: LucideIcon;
};

export const navItems: NavItem[] = [
  { label: 'Dashboard', icon: Home },
  { label: 'AI Planner', icon: Brain },
  { label: 'Processing', icon: Gauge },
  { label: 'Files & Syncing', icon: ListChecks },
  { label: 'Settings', icon: SlidersHorizontal }
];

export const statusCards: StatusCard[] = [
  {
    label: 'License',
    title: 'Pro Plan',
    value: 'A1001',
    meta: ['Valid until 2025-12-31'],
    tone: 'green',
    icon: ShieldCheck
  },
  {
    label: 'Dropbox',
    title: 'Connected',
    value: '/OMI/A1001/',
    meta: ['Last sync: 10s ago'],
    tone: 'blue',
    icon: Cloud
  },
  {
    label: 'Local Agent',
    title: 'Running',
    value: 'v0.9.0',
    meta: ['Uptime: 2h 14m'],
    tone: 'blue',
    icon: Monitor
  },
  {
    label: 'Cloud Service',
    title: 'Online',
    value: 'Queue: 2',
    meta: ['Avg. latency: 128ms'],
    tone: 'blue',
    icon: UploadCloud
  }
];

export const storage = {
  usedPercent: 68,
  used: '1.2 TB',
  total: '2 TB'
};

export const projectStats = [
  { label: 'Light Frames', value: '82 / 120', meta: 'Frames' },
  { label: 'Total Size', value: '23.6 GB', meta: '' },
  { label: 'Steps Completed', value: '5 / 7', meta: '' },
  { label: 'Elapsed Time', value: '00:12:45', meta: 'HH:MM:SS' },
  { label: 'Est. Remaining', value: '00:12:45', meta: 'HH:MM:SS' }
];

export const pipelineSteps = [
  { label: 'Ingest', status: 'done' },
  { label: 'Calibration', status: 'done' },
  { label: 'Registration', status: 'done' },
  { label: 'Integration', status: 'active' },
  { label: 'Color Calibration', status: 'pending' },
  { label: 'Master Output', status: 'pending' },
  { label: 'Completed', status: 'pending' }
] as const;

export const plannerTargets = [
  {
    rank: 1,
    name: 'M101 - Pinwheel Galaxy',
    score: 92,
    altitude: '68°',
    visibility: '6.2 h',
    moon: 'Low',
    filters: 'L, R, G, B',
    exposure: 'L 180s x 60, RGB 120s x 20 each',
    tone: 'blue'
  },
  {
    rank: 2,
    name: 'M51 - Whirlpool Galaxy',
    score: 88,
    altitude: '55°',
    visibility: '5.1 h',
    moon: 'Low',
    filters: 'L, R, G, B',
    exposure: 'L 180s x 50, RGB 120s x 20 each',
    tone: 'blue'
  },
  {
    rank: 3,
    name: 'NGC7000 - North America Nebula',
    score: 84,
    altitude: '62°',
    visibility: '4.8 h',
    moon: 'Medium',
    filters: 'Ha, OIII, SII',
    exposure: 'Ha 300s x 30, OIII 300s x 20, SII 300s x 20',
    tone: 'amber'
  }
];

export const logs = [
  ['22:31:08', 'INFO', 'New frame detected: M31_L_0082.fit'],
  ['22:31:12', 'INFO', 'File stable, added to queue'],
  ['22:31:18', 'INFO', 'Dropbox sync completed'],
  ['22:31:22', 'INFO', 'Upload confirmed'],
  ['22:32:40', 'INFO', 'Cloud calibration started'],
  ['22:33:11', 'INFO', 'Calibration completed'],
  ['22:33:15', 'INFO', 'Registration started'],
  ['22:35:42', 'INFO', 'Registration completed'],
  ['22:40:25', 'INFO', 'Master_L updated'],
  ['22:40:25', 'INFO', 'Integration progress: 68%'],
  ['22:40:25', 'INFO', 'Estimated time remaining: 12m 45s']
];

export const quickActions = [
  { label: 'New Project', icon: Plus },
  { label: 'Open Project', icon: Folder },
  { label: 'Check Sync', icon: RefreshCcw },
  { label: 'Processing Queue', icon: ListChecks },
  { label: 'Open Output Folder', icon: HardDrive },
  { label: 'System Settings', icon: Gauge }
];

export const systemStatus = [
  ['License', 'Active'],
  ['Dropbox', 'Connected'],
  ['Local Agent', 'Running'],
  ['Cloud Service', 'Online'],
  ['Storage', '1.2 TB Free']
];
