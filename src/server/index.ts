import Fastify from 'fastify';
import { config } from '../config';
import { registerRoutes } from './routes';
import { runMigrations } from '../db/migrations';

const fastify = Fastify({ logger: true });

async function start() {
  runMigrations();

  await registerRoutes(fastify);

  try {
    await fastify.listen({ port: config.port, host: '0.0.0.0' });
    console.log(`Server listening on http://localhost:${config.port}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
}

start();