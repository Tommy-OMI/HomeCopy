import { dialog } from 'electron';
import { existsSync } from 'node:fs';
import { getAuthState } from './auth';
import { getAccessToken } from './auth';
import { getJsonSetting, setJsonSetting } from './settings';
import { getSyncState, getSyncWatcherState, startSyncWatcher } from './sync';
import { wixConfig } from './wixConfig';

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

export type ActivateLicenseInput = {
  licenseKey: string;
};

const licenseKey = 'license.state';
export const getLicenseState = (): LicenseState => {
  return (
    getJsonSetting<LicenseState>(licenseKey) ?? {
      isActive: false,
      licenseKey: '',
      accountId: '',
      plan: '',
      validUntil: '',
      dropboxSharedLink: '',
      associatedLocalPath: '',
      activatedAt: ''
    }
  );
};

export const activateLicense = async (input: ActivateLicenseInput): Promise<LicenseState> => {
  const auth = getAuthState();
  const accessToken = getAccessToken();
  const key = input.licenseKey.trim();

  if (!auth.isLoggedIn || !auth.user) {
    throw new Error('Please log in before activating a license.');
  }

  if (!key) {
    throw new Error('License key is required.');
  }

  const response = await fetch(wixConfig.licenseActivationEndpoint, {
    method: 'POST',
    headers: {
      authorization: accessToken ? `Bearer ${accessToken}` : '',
      'wix-site-id': wixConfig.siteId,
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      licenseKey: key,
      memberId: auth.user.memberId,
      contactId: auth.user.contactId,
      email: auth.user.email
    })
  });

  if (!response.ok) {
    throw new Error(`License API returned ${response.status}.`);
  }

  const body = (await response.json()) as Partial<LicenseState> & {
    ok?: boolean;
    error?: string;
    dropbox_shared_link?: string;
    account_id?: string;
    valid_until?: string;
  };

  if (body.ok === false) {
    throw new Error(body.error ?? 'License activation failed.');
  }

  const sync = getSyncState();
  const state: LicenseState = {
    isActive: true,
    licenseKey: key,
    accountId: body.accountId ?? body.account_id ?? '',
    plan: body.plan ?? 'Pro Plan',
    validUntil: body.validUntil ?? body.valid_until ?? '',
    dropboxSharedLink: body.dropboxSharedLink ?? body.dropbox_shared_link ?? '',
    associatedLocalPath: sync.syncRoot ?? '',
    activatedAt: new Date().toISOString()
  };

  setJsonSetting(licenseKey, state);
  return state;
};

export const chooseDropboxAssociation = async (): Promise<LicenseState> => {
  const current = getLicenseState();
  const detectedSync = getSyncState();
  const result = await dialog.showOpenDialog({
    title: 'Choose local Dropbox sync folder',
    defaultPath: current.associatedLocalPath || detectedSync.syncRoot || undefined,
    properties: ['openDirectory']
  });

  if (result.canceled || result.filePaths.length === 0) {
    return current;
  }

  const next = {
    ...current,
    associatedLocalPath: result.filePaths[0]
  };
  setJsonSetting(licenseKey, next);
  startSyncWatcher();
  return next;
};

export const confirmDetectedDropboxAssociation = (): LicenseState => {
  const current = getLicenseState();
  const detectedSync = getSyncState();

  if (!detectedSync.syncRoot) {
    throw new Error('No local Dropbox sync folder was detected.');
  }

  const next = {
    ...current,
    associatedLocalPath: detectedSync.syncRoot
  };
  setJsonSetting(licenseKey, next);
  startSyncWatcher();
  return next;
};

export const getStartupChecks = (): StartupCheck[] => {
  const auth = getAuthState();
  const license = getLicenseState();
  const watcher = getSyncWatcherState();

  return [
    {
      id: 'user-login',
      label: 'User login',
      status: auth.isLoggedIn ? 'passed' : 'failed',
      detail: auth.isLoggedIn ? `Logged in as ${auth.user?.email || auth.user?.name}` : 'Guest session'
    },
    {
      id: 'license-activation',
      label: 'License activation',
      status: license.isActive ? 'passed' : 'failed',
      detail: license.isActive ? `${license.plan || 'Active license'} ${license.validUntil ? `valid until ${license.validUntil}` : ''}` : 'No active license'
    },
    {
      id: 'dropbox-shared-link',
      label: 'Dropbox shared link',
      status: license.dropboxSharedLink ? 'passed' : license.isActive ? 'failed' : 'placeholder',
      detail: license.dropboxSharedLink ? 'Shared link returned by Wix license API' : license.isActive ? 'License is active but no Dropbox shared link is stored' : 'Waiting for license activation'
    },
    {
      id: 'dropbox-local-association',
      label: 'Local Dropbox association',
      status: license.associatedLocalPath && existsSync(license.associatedLocalPath) ? 'passed' : license.isActive ? 'failed' : 'placeholder',
      detail:
        license.associatedLocalPath && existsSync(license.associatedLocalPath)
          ? license.associatedLocalPath
          : license.isActive
            ? 'Choose the local Dropbox folder mapped to the assigned shared folder'
            : 'Waiting for license activation'
    },
    {
      id: 'local-agent',
      label: 'Local Agent',
      status: watcher.running ? 'passed' : 'failed',
      detail: watcher.running ? `Watching ${watcher.root}` : 'Local FITS watcher is not running'
    }
  ];
};
