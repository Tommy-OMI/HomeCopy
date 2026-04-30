import { getDatabase } from './database';

export const setSetting = (key: string, value: string): void => {
  getDatabase().prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value').run(key, value);
};

export const getSetting = (key: string): string | null => {
  const row = getDatabase().prepare('SELECT value FROM settings WHERE key = ?').get(key) as { value: string } | undefined;
  return row?.value ?? null;
};

export const setJsonSetting = (key: string, value: unknown): void => {
  setSetting(key, JSON.stringify(value));
};

export const getJsonSetting = <T>(key: string): T | null => {
  const value = getSetting(key);
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
};

