import Database from 'better-sqlite3';
import path from 'path';
import { config } from '../config';
import { PublishLog } from '../types';

const dbPath = path.resolve(config.dbPath);
const db = new Database(dbPath);

// Create table if not exists
db.exec(`
  CREATE TABLE IF NOT EXISTS publish_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    platform TEXT NOT NULL,
    variant TEXT NOT NULL,
    post_url TEXT NOT NULL,
    utm_url TEXT NOT NULL,
    status TEXT NOT NULL,
    response_json TEXT
  )
`);

export function logPublishAttempt(log: Omit<PublishLog, 'id'>): void {
  const stmt = db.prepare(`
    INSERT INTO publish_logs (timestamp, platform, variant, post_url, utm_url, status, response_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  stmt.run(log.timestamp, log.platform, log.variant, log.post_url, log.utm_url, log.status, log.response_json);
}

export function getLogs(): PublishLog[] {
  const stmt = db.prepare('SELECT * FROM publish_logs ORDER BY timestamp DESC');
  return stmt.all() as PublishLog[];
}

export { db };