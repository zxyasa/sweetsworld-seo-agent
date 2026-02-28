"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fastify_1 = __importDefault(require("fastify"));
const config_1 = require("../config");
const routes_1 = require("./routes");
const migrations_1 = require("../db/migrations");
const fastify = (0, fastify_1.default)({ logger: true });
async function start() {
    (0, migrations_1.runMigrations)();
    await (0, routes_1.registerRoutes)(fastify);
    try {
        await fastify.listen({ port: config_1.config.port, host: '0.0.0.0' });
        console.log(`Server listening on http://localhost:${config_1.config.port}`);
    }
    catch (err) {
        fastify.log.error(err);
        process.exit(1);
    }
}
start();
