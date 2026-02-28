"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.db = void 0;
exports.logPublishAttempt = logPublishAttempt;
exports.getLogs = getLogs;
const better_sqlite3_1 = __importDefault(require("better-sqlite3"));
const path_1 = __importDefault(require("path"));
const config_1 = require("../config");
const dbPath = path_1.default.resolve(config_1.config.dbPath);
const db = new better_sqlite3_1.default(dbPath);
exports.db = db;
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
function logPublishAttempt(log) {
    const stmt = db.prepare(`
    INSERT INTO publish_logs (timestamp, platform, variant, post_url, utm_url, status, response_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
    stmt.run(log.timestamp, log.platform, log.variant, log.post_url, log.utm_url, log.status, log.response_json);
}
function getLogs() {
    const stmt = db.prepare('SELECT * FROM publish_logs ORDER BY timestamp DESC');
    return stmt.all();
}
