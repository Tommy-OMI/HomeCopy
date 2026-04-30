import { BrowserWindow, app } from 'electron';
import { createHash, randomBytes, randomUUID } from 'node:crypto';
import { getJsonSetting, getSetting, setJsonSetting, setSetting } from './settings';
import { wixConfig } from './wixConfig';

export type AuthUser = {
  memberId: string;
  contactId: string;
  email: string;
  name: string;
  photoUrl: string;
  loggedInAt: string;
};

export type AuthTokens = {
  accessToken: string;
  refreshToken: string | null;
  expiresAt: string;
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

const authUserKey = 'auth.user';
const authTokensKey = 'auth.tokens';
const authPkceKey = 'auth.pkce';
const authLastErrorKey = 'auth.last_error';
const authLastStepKey = 'auth.last_step';
const callbackPrefix = `${wixConfig.callbackScheme}://auth`;

export const getAuthState = (): AuthState => {
  const user = getJsonSetting<AuthUser>(authUserKey);
  const tokens = getJsonSetting<AuthTokens>(authTokensKey);

  return {
    isLoggedIn: Boolean(user),
    user,
    hasRefreshToken: Boolean(tokens?.refreshToken),
    expiresAt: tokens?.expiresAt ?? '',
    callbackScheme: callbackPrefix,
    lastError: getSetting(authLastErrorKey) ?? '',
    lastStep: getSetting(authLastStepKey) ?? ''
  };
};

let pendingLoginResolver: ((state: AuthState) => void) | null = null;
let pendingLoginRejecter: ((error: unknown) => void) | null = null;

export const openLoginWindow = (parent?: BrowserWindow | null): Promise<AuthState> => {
  return new Promise((resolve, reject) => {
    setAuthStep('Opening Wix hosted login');
    setSetting(authLastErrorKey, '');

    const loginWindow = new BrowserWindow({
      width: 520,
      height: 760,
      parent: parent ?? undefined,
      modal: Boolean(parent),
      title: 'OMI Astro Login',
      autoHideMenuBar: true,
      backgroundColor: '#070b14',
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false
      }
    });

    let settled = false;

    const finish = (state: AuthState): void => {
      if (settled) {
        return;
      }
      settled = true;
      if (!loginWindow.isDestroyed()) {
        loginWindow.close();
      }
      resolve(state);
    };

    pendingLoginResolver = finish;
    pendingLoginRejecter = reject;

    const handleUrl = (url: string): boolean => {
      if (!isOAuthCallbackUrl(url)) {
        return false;
      }

      setAuthStep(`OAuth callback captured: ${sanitizeCallbackUrl(url)}`);
      handleCallback(url)
        .then(finish)
        .catch((error: unknown) => {
          setAuthError(error);
          if (!settled) {
            settled = true;
            reject(error);
          }
        });
      return true;
    };

    loginWindow.webContents.on('will-navigate', (event, url) => {
      if (handleUrl(url)) {
        event.preventDefault();
      }
    });

    loginWindow.webContents.on('will-redirect', (event, url) => {
      if (handleUrl(url)) {
        event.preventDefault();
      }
    });

    loginWindow.webContents.on('did-navigate', (_event, url) => {
      handleUrl(url);
    });

    loginWindow.webContents.on('did-redirect-navigation', (_event, url) => {
      handleUrl(url);
    });

    loginWindow.webContents.on('did-fail-load', (_event, _errorCode, errorDescription, validatedUrl) => {
      if (validatedUrl && handleUrl(validatedUrl)) {
        return;
      }

      if (errorDescription) {
        setAuthStep(`Login window load warning: ${errorDescription}`);
      }
    });

    loginWindow.webContents.setWindowOpenHandler(({ url }) => {
      if (handleUrl(url)) {
        return { action: 'deny' };
      }

      return { action: 'allow' };
    });

    loginWindow.once('closed', () => {
      if (!settled) {
        settled = true;
        resolve(getAuthState());
      }
    });

    buildLoginUrl()
      .then((url) => {
        setAuthStep('Wix redirect session created');
        return loginWindow.loadURL(url);
      })
      .catch((error) => {
        setAuthError(error);
        if (!settled) {
          settled = true;
          reject(error);
        }
      });
  });
};

export const logout = (): AuthState => {
  setSetting(authUserKey, '');
  setSetting(authTokensKey, '');
  setSetting(authPkceKey, '');
  setAuthStep('Logged out');
  return getAuthState();
};

export const registerProtocol = (): void => {
  if (process.defaultApp) {
    app.setAsDefaultProtocolClient(wixConfig.callbackScheme, process.execPath, [process.argv[1]]);
    return;
  }

  app.setAsDefaultProtocolClient(wixConfig.callbackScheme);
};

export const handleExternalAuthUrl = async (url: string): Promise<boolean> => {
  if (!isOAuthCallbackUrl(url)) {
    return false;
  }

  try {
    setAuthStep(`External OAuth callback captured: ${sanitizeCallbackUrl(url)}`);
    const state = await handleCallback(url);
    pendingLoginResolver?.(state);
  } catch (error) {
    setAuthError(error);
    pendingLoginRejecter?.(error);
  } finally {
    pendingLoginResolver = null;
    pendingLoginRejecter = null;
  }

  return true;
};

export const getAccessToken = (): string | null => {
  return getJsonSetting<AuthTokens>(authTokensKey)?.accessToken ?? null;
};

const buildLoginUrl = async (): Promise<string> => {
  setAuthStep('Generating PKCE challenge');
  const codeVerifier = base64Url(randomBytes(32));
  const codeChallenge = base64Url(createHash('sha256').update(codeVerifier).digest());
  const state = randomUUID();
  setJsonSetting(authPkceKey, { codeVerifier, state });

  const visitorToken = await getVisitorToken();
  setAuthStep('Anonymous visitor token acquired');
  const response = await fetch(wixConfig.redirectSessionEndpoint, {
    method: 'POST',
    headers: {
      authorization: `Bearer ${visitorToken}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      auth: {
        authRequest: {
          clientId: wixConfig.clientId,
          codeChallenge,
          codeChallengeMethod: 'S256',
          redirectUri: wixConfig.redirectUri,
          responseType: 'code',
          responseMode: 'query',
          state
        }
      }
    })
  });

  if (!response.ok) {
    throw new Error(`Wix redirect session failed with ${response.status}.`);
  }

  const body = (await response.json()) as { redirectSession?: { fullUrl?: string } };
  const fullUrl = body.redirectSession?.fullUrl;
  if (!fullUrl) {
    throw new Error('Wix redirect session did not return a login URL.');
  }

  return fullUrl;
};

const getVisitorToken = async (): Promise<string> => {
  const response = await fetch(wixConfig.tokenEndpoint, {
    method: 'POST',
    headers: {
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      clientId: wixConfig.clientId,
      grantType: 'anonymous'
    })
  });

  if (!response.ok) {
    throw new Error(`Wix visitor token request failed with ${response.status}.`);
  }

  const body = (await response.json()) as { access_token?: string; accessToken?: string };
  const token = body.access_token ?? body.accessToken;
  if (!token) {
    throw new Error('Wix visitor token response did not include an access token.');
  }

  return token;
};

const handleCallback = async (url: string): Promise<AuthState> => {
  setAuthStep('Parsing OAuth callback');
  const parsed = new URL(url);
  const code = parsed.searchParams.get('code') ?? getFragmentParam(parsed, 'code');
  const returnedState = parsed.searchParams.get('state') ?? getFragmentParam(parsed, 'state');
  const pkce = getJsonSetting<{ codeVerifier: string; state: string }>(authPkceKey);

  if (!code) {
    throw new Error('Wix OAuth callback did not include an authorization code.');
  }

  if (!pkce?.codeVerifier || pkce.state !== returnedState) {
    throw new Error('Wix OAuth callback state did not match the current login session.');
  }

  const tokens = await exchangeToken(code, pkce.codeVerifier);
  setJsonSetting(authTokensKey, tokens);
  setSetting('auth.last_callback_url', sanitizeCallbackUrl(url));
  const user = await fetchCurrentMember(tokens.accessToken);
  setJsonSetting(authUserKey, user);
  setAuthStep('Login completed');
  return getAuthState();
};

const exchangeToken = async (code: string, codeVerifier: string): Promise<AuthTokens> => {
  setAuthStep('Exchanging authorization code for tokens');
  const response = await fetch(wixConfig.tokenEndpoint, {
    method: 'POST',
    headers: {
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      clientId: wixConfig.clientId,
      grantType: 'authorization_code',
      code,
      redirectUri: wixConfig.redirectUri,
      codeVerifier
    })
  });

  if (!response.ok) {
    throw new Error(`Wix authorization token exchange failed with ${response.status}.`);
  }

  const body = (await response.json()) as Record<string, unknown>;
  setAuthStep(`Token response keys: ${Object.keys(body).join(', ') || 'none'}`);

  const accessToken = findTokenValue(body, ['access_token', 'accessToken']);
  const refreshToken = findTokenValue(body, ['refresh_token', 'refreshToken']);
  if (!accessToken) {
    throw new Error(`Wix token response did not include an access token. Keys: ${Object.keys(body).join(', ') || 'none'}`);
  }

  const expiresIn = findNumberValue(body, ['expires_in', 'expiresIn']) ?? 3600;
  return {
    accessToken,
    refreshToken,
    expiresAt: new Date(Date.now() + expiresIn * 1000).toISOString()
  };
};

const fetchCurrentMember = async (accessToken: string): Promise<AuthUser> => {
  setAuthStep('Fetching Wix member profile');
  const response = await fetch(wixConfig.currentMemberEndpoint, {
    headers: {
      authorization: `Bearer ${accessToken}`,
      'wix-site-id': wixConfig.siteId
    }
  });

  if (!response.ok) {
    throw new Error(`Wix current member request failed with ${response.status}.`);
  }

  const body = (await response.json()) as { member?: WixMember } & WixMember;
  const member = body.member ?? body;
  const firstName = member.contact?.firstName ?? '';
  const lastName = member.contact?.lastName ?? '';
  const contactName = `${firstName} ${lastName}`.trim();
  const name = member.profile?.nickname ?? contactName ?? member.loginEmail ?? 'OMI Member';

  return {
    memberId: member.id,
    contactId: member.contactId ?? '',
    email: member.loginEmail ?? '',
    name,
    photoUrl: member.profile?.photo?.url ?? '',
    loggedInAt: new Date().toISOString()
  };
};

const sanitizeCallbackUrl = (url: string): string => {
  const parsed = new URL(url);
  parsed.searchParams.delete('code');
  return parsed.toString();
};

const isOAuthCallbackUrl = (url: string): boolean => {
  return url.startsWith(callbackPrefix) || url.startsWith(wixConfig.redirectUri);
};

const setAuthStep = (step: string): void => {
  setSetting(authLastStepKey, step);
};

const setAuthError = (error: unknown): void => {
  const message = error instanceof Error ? error.message : String(error);
  setSetting(authLastErrorKey, message);
};

const getFragmentParam = (url: URL, key: string): string | null => {
  if (!url.hash) {
    return null;
  }

  return new URLSearchParams(url.hash.slice(1)).get(key);
};

const base64Url = (buffer: Buffer): string => {
  return buffer.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
};

const findTokenValue = (source: unknown, keys: string[]): string | null => {
  if (!source || typeof source !== 'object') {
    return null;
  }

  const record = source as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.length > 0) {
      return value;
    }

    if (value && typeof value === 'object') {
      const nestedValue = findTokenValue(value, ['value', 'token']);
      if (nestedValue) {
        return nestedValue;
      }
    }
  }

  for (const value of Object.values(record)) {
    if (value && typeof value === 'object') {
      const nestedValue = findTokenValue(value, keys);
      if (nestedValue) {
        return nestedValue;
      }
    }
  }

  return null;
};

const findNumberValue = (source: unknown, keys: string[]): number | null => {
  if (!source || typeof source !== 'object') {
    return null;
  }

  const record = source as Record<string, unknown>;
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'number') {
      return value;
    }
  }

  for (const value of Object.values(record)) {
    if (value && typeof value === 'object') {
      const nestedValue = findNumberValue(value, keys);
      if (nestedValue !== null) {
        return nestedValue;
      }
    }
  }

  return null;
};

type WixMember = {
  id: string;
  contactId?: string;
  loginEmail?: string;
  profile?: {
    nickname?: string;
    photo?: {
      url?: string;
    };
  };
  contact?: {
    firstName?: string;
    lastName?: string;
  };
};
